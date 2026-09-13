#!/usr/bin/env python3
# json.loads returns Any, so the parsed-document plumbing is inherently unknown to
# pyright; the rest of the module is checked strictly.
# pyright: reportUnknownVariableType=none, reportUnknownMemberType=none, reportUnknownArgumentType=none
"""FinPlan plugin client-side helper dispatcher.

Stdlib-only and fully type-annotated. This is the single home for the
deterministic client-side algorithms the plugin previously encoded as English
prose (and re-derived on every run):

* ``inject``      — embed raw data files into placeholder tokens in an HTML file.
* ``apply-delta`` — merge a ``manage_state`` delta (or full document) into a local
                    state file, verifying the rebuilt document against the
                    server-returned ``state_hash`` before writing.
* ``fmt``         — format integer cents as a ``$X,XXX.XX`` dollar string, or add
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

_FILE_URI_PREFIX = "file://"


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
        return 2

    try:
        html = _read_text(args.html)
    except OSError as exc:
        print(f"error: cannot read HTML file {args.html!r}: {exc}", file=sys.stderr)
        return 1

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
            return 1
        html = html.replace(token, data)

    try:
        with open(args.html, "w", encoding="utf-8") as handle:
            handle.write(html)
    except OSError as exc:
        print(f"error: cannot write HTML file {args.html!r}: {exc}", file=sys.stderr)
        return 1
    return 0


def _apply_delta_to_document(
    state: dict[str, Any], changed: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``state`` with ``changed`` applied, or ``(None, error_message)``.

    A ``person`` change replaces ``state['person']`` wholesale; a list-section
    change replaces the item with a matching id or appends it when none matches.
    """
    document = dict(state)
    section = changed.get("section")
    item = changed.get("item")
    if section == "person":
        document["person"] = item
        return document, None
    if section in _LIST_SECTIONS:
        id_key = _LIST_SECTIONS[section]
        existing = document.get(section)
        items: list[Any] = list(existing) if isinstance(existing, list) else []
        item_id = item.get(id_key) if isinstance(item, dict) else None
        for index, current in enumerate(items):
            if isinstance(current, dict) and current.get(id_key) == item_id:
                items[index] = item
                break
        else:
            items.append(item)
        document[section] = items
        return document, None
    return None, f"error: unknown delta section {section!r}"


def _describe_hash_mismatch(document: dict[str, Any], expected_hash: str) -> str | None:
    """Return an error message if ``document`` does not hash to ``expected_hash``."""
    actual_hash = compute_state_hash(document)
    if actual_hash == expected_hash:
        return None
    return (
        "error: state_hash mismatch — the document does not match the server hash "
        f"(expected {expected_hash}, got {actual_hash}). Refusing to write."
    )


def _cmd_apply_delta(args: argparse.Namespace) -> int:
    """Merge a ``manage_state`` response into the local state file.

    Nothing is written until the resulting document reproduces the response's
    ``state_hash``, computed over the same canonical JSON the server hashed — the
    check is unconditional, so a response carrying no hash is rejected rather than
    persisted. A full document (``action=create``, ``return_full_state=true``, or
    ``migrated: true`` — anything without a ``changed`` block) becomes the new state
    directly, and needs no existing ``--state`` file, so ``create`` can bootstrap a
    fresh workspace; otherwise the delta's ``changed`` block is applied to the local
    state and the rebuilt document is verified. Transient metadata is stripped before
    verifying, and nothing is added afterwards, so the bytes written are the bytes
    that were verified.
    """
    try:
        response_text = _read_text(args.response)
    except OSError as exc:
        print(f"error: cannot read response {args.response!r}: {exc}", file=sys.stderr)
        return 1
    try:
        parsed_response: Any = json.loads(response_text)
    except json.JSONDecodeError as exc:
        print(f"error: response {args.response!r} is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(parsed_response, dict):
        print(f"error: response {args.response!r} is not a JSON object", file=sys.stderr)
        return 2
    response: dict[str, Any] = parsed_response

    if "changed" not in response:
        # Full / migrated document (create, return_full_state, migrated): the
        # response *is* the new state, once its transient metadata is stripped below.
        document: dict[str, Any] = dict(response)
    else:
        changed = response["changed"]
        if not isinstance(changed, dict):
            print("error: response 'changed' block is not an object", file=sys.stderr)
            return 2
        # Only the delta path needs the prior state, and reading it any earlier makes
        # `action=create` impossible: create is precisely the case with no state file
        # yet, and it returns a full document.
        try:
            state_text = _read_text(args.state)
        except OSError as exc:
            print(f"error: cannot read state file {args.state!r}: {exc}", file=sys.stderr)
            return 1
        try:
            parsed_state: Any = json.loads(state_text)
        except json.JSONDecodeError as exc:
            print(f"error: state file {args.state!r} is not valid JSON: {exc}", file=sys.stderr)
            return 1
        if not isinstance(parsed_state, dict):
            print(f"error: state file {args.state!r} is not a JSON object", file=sys.stderr)
            return 2
        state: dict[str, Any] = parsed_state
        rebuilt, error = _apply_delta_to_document(state, changed)
        if rebuilt is None:
            print(error, file=sys.stderr)
            return 2
        document = rebuilt
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
        print(
            "error: response carries no state_hash, so it is not a state document "
            "(an error response?). Refusing to write.",
            file=sys.stderr,
        )
        return 2
    mismatch = _describe_hash_mismatch(document, expected_hash)
    if mismatch is not None:
        print(mismatch, file=sys.stderr)
        return 1

    # Nothing is defaulted in after verification: `last_updated` and
    # `schema_fingerprint` are both declared UserState fields, so every document the
    # server hashes already carries them. Filling them in here would be the one path
    # by which the bytes on disk could differ from the bytes that were verified.

    # Write to a sibling and rename over the target. A plain open(…, "w") truncates
    # the existing state before json.dump writes a byte, so a full disk or a Ctrl-C
    # mid-write would leave a truncated file with the previous state gone — and this
    # file is the only copy of the user's financial state, with no history behind it.
    # os.replace is atomic within a filesystem, and a sibling path keeps it there.
    out_path = args.out if args.out else args.state
    tmp_path = out_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_path, out_path)
    except OSError as exc:
        print(f"error: cannot write state file {out_path!r}: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_fmt(args: argparse.Namespace) -> int:
    """Print a formatted dollar string, or a cents-augmented JSON document."""
    if args.as_json:
        source = args.value if args.value else "-"
        try:
            raw = _read_text(source)
        except OSError as exc:
            print(f"error: cannot read JSON {source!r}: {exc}", file=sys.stderr)
            return 1
        try:
            document: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"error: input is not valid JSON: {exc}", file=sys.stderr)
            return 1
        json.dump(augment_cents(document), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if args.value is None:
        print("error: fmt requires an integer cents value (or --json)", file=sys.stderr)
        return 2
    try:
        cents = int(args.value)
    except ValueError:
        print(f"error: {args.value!r} is not an integer number of cents", file=sys.stderr)
        return 2
    print(format_cents(cents))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser and its subcommands."""
    parser = argparse.ArgumentParser(prog="finplan.py", description=__doc__)
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

    p_delta = subparsers.add_parser(
        "apply-delta", help="merge a manage_state response into a local state file"
    )
    p_delta.add_argument("--state", required=True, help="path to the local state.json")
    p_delta.add_argument(
        "--response", required=True, help="manage_state response file, or - for stdin"
    )
    p_delta.add_argument("--out", default=None, help="write here instead of --state")
    p_delta.set_defaults(func=_cmd_apply_delta)

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
