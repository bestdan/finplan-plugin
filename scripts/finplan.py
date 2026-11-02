#!/usr/bin/env python3
# json.loads returns Any, so the parsed-document plumbing is inherently unknown to
# pyright; the rest of the module is checked strictly.
# pyright: reportUnknownVariableType=none, reportUnknownMemberType=none, reportUnknownArgumentType=none
"""FinPlan plugin client-side helper dispatcher.

Stdlib-only and fully type-annotated. This is the single home for the
deterministic client-side algorithms the plugin previously encoded as English
prose (and re-derived on every run):

* ``inject`` — embed raw data files into placeholder tokens in an HTML file.
* ``save``   — merge a ``manage_state`` response (an update, a removal, or a full
               document) into a local state file, verifying the rebuilt document
               against the server-returned ``state_hash`` before writing.
               ``apply-delta`` is an alias.
* ``fmt``    — format integer cents as a ``$X,XXX.XX`` dollar string, or add
               ``*_dollars`` siblings for every ``*_cents`` leaf in a JSON doc.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any

# Response keys that are transport/verification metadata, never persisted state.
_TRANSIENT_KEYS: tuple[str, ...] = (
    "success",
    "message",
    "state_hash",
    "action",
    "changed",
    "migrated",
    "warnings",
    # update_goal appends these three *after* _mutation_response has hashed the
    # document (state.py `for key in (...): response[key] = establishment[key]`), so
    # they are transport metadata that was never part of what the server hashed. The
    # auto-create case that adds `provisional_account` also sets force_full, so it
    # always arrives on the full-document path — leave them out and every auto-created
    # goal fails verification.
    "provisional_account",
    "eligible_accounts",
    "candidate_owner_ids",
)

# List sections in a UserState document, keyed by the field each item is identified
# by. ``accounts`` keys on ``account_id``; every other list section keys on ``id``.
_LIST_SECTIONS: dict[str, str] = {
    "accounts": "account_id",
    "goals": "id",
    "income_streams": "id",
    "expenses": "id",
}

# The removal action for each list section. Its response carries only the removed
# item's id (``{"account_id": …}`` or ``{"id": …}``) as ``changed.item``.
_REMOVE_ACTIONS: dict[str, str] = {
    "remove_account": "accounts",
    "remove_goal": "goals",
    "remove_income_stream": "income_streams",
    "remove_expense": "expenses",
}

_FILE_URI_PREFIX = "file://"

# Exit codes, shared for good by finplan.py and the fpt CLI that takes its commands
# over: a caller branches on the code without parsing text. finplan.py uses 0, 2, 3
# and 4 today; the rest are reserved so the commands that talk to the server add no
# codes of their own. 1 stays what Python itself exits with on an uncaught error.
EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_VALIDATION = 2
EXIT_HASH_MISMATCH = 3
EXIT_LOCAL_IO = 4
EXIT_AUTH = 5
EXIT_NETWORK = 6
EXIT_SERVER = 7

_EXIT_CODE_NAMES: dict[int, str] = {
    EXIT_INTERNAL: "internal",
    EXIT_VALIDATION: "validation",
    EXIT_HASH_MISMATCH: "hash_mismatch",
    EXIT_LOCAL_IO: "local_io",
    EXIT_AUTH: "auth",
    EXIT_NETWORK: "network",
    EXIT_SERVER: "server",
}

EXIT_CODES_HELP = """\
exit codes (shared with fpt; one table for every command):
  0  success
  1  internal error (an uncaught exception; a bug)
  2  validation: bad arguments, a malformed response or state file, or a
     removal whose target is missing or ambiguous
  3  hash mismatch or stale write: the rebuilt document does not match the
     server's state_hash; nothing was written
  4  local I/O: a file could not be read or written
  5  authentication (reserved)
  6  network (reserved)
  7  server error (reserved)
"""


def compute_state_hash(document: dict[str, Any]) -> str:
    """Content hash of a full state document, matching the MCP server.

    SHA-256 over the canonical (sorted-key, compact) JSON of the document, prefixed
    ``sha256:``. This mirrors ``compute_state_hash`` in the MCP server's
    ``tools/state.py`` byte-for-byte, so a client that reconstructs the full
    document from a delta can verify it against the server-returned hash.
    """
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_cents(cents: int) -> str:
    """Format integer cents as ``$X,XXX.XX`` (thousands-separated, two decimals)."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}${whole:,}.{frac:02d}"


def augment_cents(value: Any) -> Any:
    """Recursively copy ``value``, adding a ``*_dollars`` sibling for each ``*_cents``.

    For every mapping key ending in ``_cents`` whose value is an ``int`` (but not a
    ``bool``), a sibling key with ``_cents`` replaced by ``_dollars`` is added,
    carrying the :func:`format_cents` rendering. Lists and scalars pass through.
    """
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            result[key] = augment_cents(child)
            if key.endswith("_cents") and isinstance(child, int) and not isinstance(child, bool):
                result[key[: -len("_cents")] + "_dollars"] = format_cents(child)
        return result
    if isinstance(value, list):
        return [augment_cents(item) for item in value]
    return value


def _read_text(source: str) -> str:
    """Read text from a file path, or from stdin when ``source`` is ``-``."""
    if source == "-":
        return sys.stdin.read()
    with open(source, encoding="utf-8") as handle:
        return handle.read()


def _cmd_inject(args: argparse.Namespace) -> int:
    """Replace placeholder tokens in an HTML file with raw data-file contents.

    ``pairs`` is a flat ``TOKEN data_path [TOKEN data_path ...]`` list. Each data
    path may carry a leading ``file://`` (stripped). A token absent from the HTML —
    which also means its data file goes unused — is a stderr warning, not an error.
    The only non-zero exits are for unreadable files.
    """
    pairs: list[str] = list(args.pairs)
    if len(pairs) == 0 or len(pairs) % 2 != 0:
        print(
            "error: inject expects an HTML file followed by TOKEN/data-path pairs",
            file=sys.stderr,
        )
        return EXIT_VALIDATION

    try:
        html = _read_text(args.html)
    except OSError as exc:
        print(f"error: cannot read HTML file {args.html!r}: {exc}", file=sys.stderr)
        return EXIT_LOCAL_IO

    tokens = pairs[0::2]
    data_paths = pairs[1::2]
    # Plain zip, no strict=: the even-length check above already guarantees the two
    # slices are the same length, and the keyword is 3.10+ — this module has to run
    # on whatever python3 the plugin's user has, which on stock macOS is 3.9.
    for token, data_path in zip(tokens, data_paths):
        if token not in html:
            print(
                f"warning: token {token!r} not found in {args.html}; "
                f"data file {data_path!r} is unused",
                file=sys.stderr,
            )
            continue
        if data_path.startswith(_FILE_URI_PREFIX):
            path = data_path[len(_FILE_URI_PREFIX) :]
        else:
            path = data_path
        try:
            data = _read_text(path)
        except OSError as exc:
            print(f"error: cannot read data file {path!r}: {exc}", file=sys.stderr)
            return EXIT_LOCAL_IO
        html = html.replace(token, data)

    try:
        with open(args.html, "w", encoding="utf-8") as handle:
            handle.write(html)
    except OSError as exc:
        print(f"error: cannot write HTML file {args.html!r}: {exc}", file=sys.stderr)
        return EXIT_LOCAL_IO
    return EXIT_OK


class _SaveError(Exception):
    """A ``save`` failure, reported to stderr as one JSON object.

    ``pointer`` is a JSON Pointer (RFC 6901) into the document named by
    ``source`` — the response or the state file — following RFC 9457's
    ``errors[].pointer``. ``hint`` says what to change, and where an obvious wrong
    move exists, what not to do instead.
    """

    def __init__(
        self,
        exit_code: int,
        message: str,
        hint: str,
        pointer: str | None = None,
        source: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.message = message
        self.hint = hint
        self.pointer = pointer
        self.source = source
        self.details = details or {}

    def to_json(self) -> dict[str, Any]:
        """The stderr payload: what failed, where, and what to change."""
        payload: dict[str, Any] = {
            "error": _EXIT_CODE_NAMES[self.exit_code],
            "exit_code": self.exit_code,
            "message": self.message,
            "source": self.source,
            "pointer": self.pointer,
            "hint": self.hint,
        }
        payload.update(self.details)
        return payload


_DO_NOT_HAND_WRITE = (
    "Do not write the state file by hand or with a shell redirect to get around this."
)


def _load_json_object(path: str, label: str) -> dict[str, Any]:
    """Read ``path`` (``-`` for stdin) as a JSON object, or raise :class:`_SaveError`."""
    try:
        text = _read_text(path)
    except OSError as exc:
        raise _SaveError(
            EXIT_LOCAL_IO,
            f"cannot read {label} {path!r}: {exc}",
            f"Check that {path!r} exists and is readable.",
            source=label,
        ) from exc
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise _SaveError(
            EXIT_VALIDATION,
            f"{label} {path!r} is not valid JSON: {exc}",
            f"Pass the {label} exactly as produced, unedited.",
            pointer="",
            source=label,
        ) from exc
    if not isinstance(parsed, dict):
        raise _SaveError(
            EXIT_VALIDATION,
            f"{label} {path!r} is not a JSON object",
            f"The {label} must be a JSON object.",
            pointer="",
            source=label,
        )
    return parsed


def _matching_indexes(items: list[Any], id_key: str, item_id: Any) -> list[int]:
    """Indexes of every entry in ``items`` whose ``id_key`` equals ``item_id``."""
    return [
        index
        for index, current in enumerate(items)
        if isinstance(current, dict) and current.get(id_key) == item_id
    ]


def _apply_delta_to_document(
    state: dict[str, Any], changed: dict[str, Any], action: Any = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``state`` with ``changed`` applied, and a summary of the change.

    A ``person`` change (``update_person``, ``set_spouse``, ``clear_spouse``)
    replaces ``state['person']`` wholesale with the server's merged person. A
    list-section change replaces the item with a matching id or appends it when
    none matches. A ``remove_*`` action deletes the one item with that id, and
    refuses when no item or more than one carries it: the server removes the first
    match only, so a duplicate here means the local file is not the document the
    server edited.

    The summary is ``{"change", "section", "item_id", "item"}``: ``item`` is the
    entry that changes — the new one for an update, the removed one for a removal.

    Raises:
        _SaveError: an unknown section, a removal for the wrong section, or a
            removal whose target is missing or ambiguous (all validation errors).
    """
    document = dict(state)
    section = changed.get("section")
    item = changed.get("item")
    if section == "person":
        document["person"] = item
        return document, {"change": "replaced", "section": section, "item_id": None, "item": item}
    if section not in _LIST_SECTIONS:
        raise _SaveError(
            EXIT_VALIDATION,
            f"unknown delta section {section!r}",
            "Pass the manage_state response unedited; 'changed.section' must be one of "
            + ", ".join(["person"] + sorted(_LIST_SECTIONS)),
            pointer="/changed/section",
            source="response",
            details={"expected": ["person"] + sorted(_LIST_SECTIONS), "found": section},
        )
    id_key = _LIST_SECTIONS[section]
    existing = document.get(section)
    items: list[Any] = list(existing) if isinstance(existing, list) else []
    item_id = item.get(id_key) if isinstance(item, dict) else None
    matches = _matching_indexes(items, id_key, item_id)

    if action in _REMOVE_ACTIONS:
        expected_section = _REMOVE_ACTIONS[action]
        if section != expected_section:
            raise _SaveError(
                EXIT_VALIDATION,
                f"{action} must change section {expected_section!r}, not {section!r}",
                "Pass the manage_state response unedited.",
                pointer="/changed/section",
                source="response",
                details={"expected": expected_section, "found": section},
            )
        # Checked before matching: a None id would otherwise match any entry that
        # also lacks the key, and the error would surface as a hash mismatch.
        if item_id is None:
            raise _SaveError(
                EXIT_VALIDATION,
                f"{action}: response changed.item carries no {id_key}",
                "Pass the manage_state response unedited.",
                pointer=f"/changed/item/{id_key}",
                source="response",
                details={"expected": id_key, "found": item},
            )
        if len(matches) != 1:
            problem = "no" if not matches else f"{len(matches)}"
            raise _SaveError(
                EXIT_VALIDATION,
                f"{action}: the state file has {problem} {section} entries with "
                f"{id_key}={item_id!r}, so the removal has no single target",
                "The state file is not the document the server edited. Re-read the state "
                "file and run the removal against it again. " + _DO_NOT_HAND_WRITE,
                pointer=f"/changed/item/{id_key}",
                source="response",
                details={"id": item_id, "expected": 1, "found": len(matches)},
            )
        removed = items.pop(matches[0])
        document[section] = items
        return document, {
            "change": "removed",
            "section": section,
            "item_id": item_id,
            "item": removed,
        }

    if matches:
        items[matches[0]] = item
        change = "updated"
    else:
        items.append(item)
        change = "added"
    document[section] = items
    return document, {"change": change, "section": section, "item_id": item_id, "item": item}


def _verify_hash(document: dict[str, Any], expected_hash: str) -> None:
    """Raise :class:`_SaveError` unless ``document`` hashes to ``expected_hash``."""
    actual_hash = compute_state_hash(document)
    if actual_hash == expected_hash:
        return
    raise _SaveError(
        EXIT_HASH_MISMATCH,
        "state_hash mismatch — the document does not match the server hash "
        f"(expected {expected_hash}, got {actual_hash}). Refusing to write.",
        "Nothing was written; the state file is unchanged. Re-read it, redo the edit "
        "against it, and save the new response. " + _DO_NOT_HAND_WRITE,
        pointer="/state_hash",
        source="response",
        details={"expected": expected_hash, "found": actual_hash},
    )


def _input_hash(path: str) -> str | None:
    """Content hash of the state file before the save, or None when there is none.

    Only the full-document path calls this; a delta has already parsed the file.
    A missing or unparseable file is not an error there — ``create`` and a
    migrated document both replace the file outright.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            parsed: Any = json.load(handle)
    except (OSError, ValueError):
        return None
    return compute_state_hash(parsed) if isinstance(parsed, dict) else None


def _save(args: argparse.Namespace) -> dict[str, Any]:
    """Run ``save`` and return its envelope, or raise :class:`_SaveError`."""
    response = _load_json_object(args.response, "response")
    warnings: list[Any] = []
    response_warnings = response.get("warnings")
    if isinstance(response_warnings, list):
        warnings.extend(response_warnings)

    if "changed" not in response:
        # Full / migrated document (create, return_full_state, migrated): the
        # response *is* the new state, once its transient metadata is stripped below.
        document: dict[str, Any] = dict(response)
        input_hash = _input_hash(args.state)
        summary: dict[str, Any] = {
            "change": "replaced",
            "section": None,
            "item_id": None,
            "item": None,
        }
    else:
        changed = response["changed"]
        if not isinstance(changed, dict):
            raise _SaveError(
                EXIT_VALIDATION,
                "response 'changed' block is not an object",
                "Pass the manage_state response unedited.",
                pointer="/changed",
                source="response",
            )
        # Only the delta path needs the prior state, and reading it any earlier makes
        # `action=create` impossible: create is precisely the case with no state file
        # yet, and it returns a full document.
        state = _load_json_object(args.state, "state file")
        input_hash = compute_state_hash(state)
        document, summary = _apply_delta_to_document(state, changed, response.get("action"))
        # The server stamps last_updated during the mutation and hashes the result,
        # so the rebuilt document must carry the server's value to reproduce the hash.
        if "last_updated" in response:
            document["last_updated"] = response["last_updated"]

    # Transient metadata is never part of what the server hashed, so strip it before
    # verifying rather than after.
    for key in _TRANSIENT_KEYS:
        document.pop(key, None)

    # One invariant, checked once for both branches: nothing is written that does not
    # reproduce the server's hash. Every response that carries state carries a
    # state_hash, so one that doesn't is not a state document — most often an error
    # response, which has no `changed` key and would otherwise strip down to an empty
    # document and overwrite the local state.
    expected_hash = response.get("state_hash")
    if not isinstance(expected_hash, str):
        raise _SaveError(
            EXIT_VALIDATION,
            "response carries no state_hash, so it is not a state document "
            "(an error response?). Refusing to write.",
            "Save only a successful manage_state response. If the call failed, fix the "
            "call rather than the state file.",
            pointer="/state_hash",
            source="response",
            details={"found": response.get("message")},
        )
    _verify_hash(document, expected_hash)

    out_path = args.out if args.out else args.state
    data: dict[str, Any] = {
        "action": response.get("action"),
        "change": summary["change"],
        "section": summary["section"],
        "item_id": summary["item_id"],
        "path": out_path,
        "written": not args.dry_run,
    }
    if args.dry_run:
        data["item"] = summary["item"]
    else:
        # Nothing is defaulted in after verification: `last_updated` and
        # `schema_fingerprint` are both declared UserState fields, so every document
        # the server hashes already carries them. Filling them in here would be the
        # one path by which the bytes on disk could differ from the bytes verified.
        _write_document(document, out_path)
    return {
        "data": data,
        "metadata": {
            "input_hash": input_hash,
            "result_hash": expected_hash,
            "warnings": warnings,
        },
    }


def _write_document(document: dict[str, Any], out_path: str) -> None:
    """Write ``document`` to ``out_path`` atomically, or raise :class:`_SaveError`.

    Write to a sibling and rename over the target. A plain open(…, "w") truncates
    the existing state before json.dump writes a byte, so a full disk or a Ctrl-C
    mid-write would leave a truncated file with the previous state gone — and this
    file is the only copy of the user's financial state, with no history behind it.
    os.replace is atomic within a filesystem, and a sibling path keeps it there.
    """
    tmp_path = out_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_path, out_path)
    except OSError as exc:
        raise _SaveError(
            EXIT_LOCAL_IO,
            f"cannot write state file {out_path!r}: {exc}",
            "Check that the directory exists and is writable; the previous file is "
            "unchanged. " + _DO_NOT_HAND_WRITE,
            source="state file",
        ) from exc


def _cmd_save(args: argparse.Namespace) -> int:
    """Merge a ``manage_state`` response into the local state file.

    Nothing is written until the resulting document reproduces the response's
    ``state_hash``, computed over the same canonical JSON the server hashed — the
    check is unconditional, so a response carrying no hash is rejected rather than
    persisted. A full document (``action=create``, ``return_full_state=true``, or
    ``migrated: true`` — anything without a ``changed`` block) becomes the new state
    directly, and needs no existing ``--state`` file, so ``create`` can bootstrap a
    fresh workspace; otherwise the delta's ``changed`` block is applied to the local
    state — an update, a ``remove_*``, or a person change — and the rebuilt
    document is verified. Transient metadata is stripped before verifying, and
    nothing is added afterwards, so the bytes written are the bytes that were
    verified.

    Standard output carries one JSON envelope and nothing else: ``data`` says what
    changed, ``metadata`` carries the input and result content hashes and the
    server's ``warnings``. A failure prints one JSON object to standard error and
    exits with a code from :data:`EXIT_CODES_HELP`. ``--dry-run`` does all of the
    above, adds the changing item to ``data``, and writes nothing.
    """
    try:
        envelope = _save(args)
    except _SaveError as exc:
        sys.stderr.write(json.dumps(exc.to_json(), ensure_ascii=False) + "\n")
        return exc.exit_code
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False) + "\n")
    return EXIT_OK


def _cmd_fmt(args: argparse.Namespace) -> int:
    """Print a formatted dollar string, or a cents-augmented JSON document."""
    if args.as_json:
        source = args.value if args.value else "-"
        try:
            raw = _read_text(source)
        except OSError as exc:
            print(f"error: cannot read JSON {source!r}: {exc}", file=sys.stderr)
            return EXIT_LOCAL_IO
        try:
            document: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"error: input is not valid JSON: {exc}", file=sys.stderr)
            return EXIT_VALIDATION
        json.dump(augment_cents(document), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return EXIT_OK

    if args.value is None:
        print("error: fmt requires an integer cents value (or --json)", file=sys.stderr)
        return EXIT_VALIDATION
    try:
        cents = int(args.value)
    except ValueError:
        print(f"error: {args.value!r} is not an integer number of cents", file=sys.stderr)
        return EXIT_VALIDATION
    print(format_cents(cents))
    return EXIT_OK


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser and its subcommands."""
    parser = argparse.ArgumentParser(
        prog="finplan.py",
        description=__doc__,
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_inject = subparsers.add_parser(
        "inject", help="embed data files into placeholder tokens in an HTML file"
    )
    p_inject.add_argument("html", help="the HTML file to rewrite in place")
    p_inject.add_argument(
        "pairs",
        nargs=argparse.REMAINDER,
        help="TOKEN data-path pairs (data path may start with file://)",
    )
    p_inject.set_defaults(func=_cmd_inject)

    # `apply-delta` is the old name, kept so existing callers and tests still work.
    p_save = subparsers.add_parser(
        "save",
        aliases=["apply-delta"],
        help="merge a manage_state response into a local state file",
        description=(
            "Merge a manage_state response (an update, a remove_*, a person change,\n"
            "or a full document) into the local state file, and write it only if the\n"
            "result reproduces the response's state_hash. Prints one JSON envelope on\n"
            "stdout ({data, metadata}); errors go to stderr as JSON."
        ),
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_save.add_argument("--state", required=True, help="path to the local state.json")
    p_save.add_argument(
        "--response", required=True, help="manage_state response file, or - for stdin"
    )
    p_save.add_argument("--out", default=None, help="write here instead of --state")
    p_save.add_argument(
        "--dry-run",
        action="store_true",
        help="verify and print the item that would change; write nothing",
    )
    p_save.set_defaults(func=_cmd_save)

    p_fmt = subparsers.add_parser("fmt", help="format cents as dollars")
    p_fmt.add_argument(
        "value", nargs="?", default=None, help="integer cents, or a JSON file / - with --json"
    )
    p_fmt.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="add *_dollars siblings for every *_cents leaf in a JSON document",
    )
    p_fmt.set_defaults(func=_cmd_fmt)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and dispatch to the selected subcommand."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    func: Any = args.func
    result: int = func(args)
    return result


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
