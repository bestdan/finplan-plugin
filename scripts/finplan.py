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
               ``--from-url`` installs a full document served as a download
               (``urls.data``) instead. ``apply-delta`` is an alias.
* ``hash``   — print a state file's content hash, for ``save --expect-hash``.
* ``fmt``    — format integer cents as a ``$X,XXX.XX`` dollar string, or add
               ``*_dollars`` siblings for every ``*_cents`` leaf in a JSON doc.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import http.client
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Generator
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
# over: a caller branches on the code without parsing text. finplan.py uses all but
# 5, which is reserved so the commands that talk to the server add no codes of their
# own. 1 stays what Python itself exits with on an uncaught error.
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
  2  validation: bad arguments, a malformed response or state file, a
     removal whose target is missing or ambiguous, or a --from-url that is
     not one of FinPlan's own download URLs
  3  hash mismatch or stale write: the rebuilt document does not match the
     server's state_hash, or the file changed since --expect-hash was
     recorded; nothing was written
  4  local I/O: a file could not be read or written
  5  authentication (reserved)
  6  network: a --from-url download could not reach the server
  7  server error: the server answered a --from-url download with an HTTP
     error (most often an expired link)
"""

# Where --from-url may download from. The hosted server serves downloads under
# `<base>/files/`; FINPLAN_FILE_SERVER_URL is the same override the server reads for
# its own base URL. Without it, the host comes from the plugin's .mcp.json, so a
# fork pointed at another server accepts that server's links.
_FILE_SERVER_ENV = "FINPLAN_FILE_SERVER_URL"
_DEFAULT_FILE_SERVER = "https://mcp.finplan.tools"
_MCP_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, ".mcp.json")
# A local (stdio) server writes downloads here and links them as file:// URLs. The
# default and the variable match the server's (finplan_core.io.finplan_temp_dir).
_DATA_DIR_ENV = "FINPLAN_DATA_DIR"
_DEFAULT_DATA_DIR = "/tmp/finplan"
# The server refuses to write a download larger than this (MAX_BUNDLE_SIZE_BYTES).
_MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
_DOWNLOAD_TIMEOUT_SECONDS = 60


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
        error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        # Code 3 covers two failures a caller recovers from differently, so the
        # name, not the code, tells a stale write from a hash mismatch.
        self.error = error or _EXIT_CODE_NAMES[exit_code]
        self.message = message
        self.hint = hint
        self.pointer = pointer
        self.source = source
        self.details = details or {}

    def to_json(self) -> dict[str, Any]:
        """The stderr payload: what failed, where, and what to change."""
        payload: dict[str, Any] = {
            "error": self.error,
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


class _Destination:
    """What the file a save would replace held when it was read.

    ``data`` is the raw bytes (None when the file is absent); ``content_hash`` is
    :func:`content_hash` of them; ``state_hash`` is the server-comparable hash, or
    None when the bytes are not a JSON object.
    """

    def __init__(self, data: bytes | None) -> None:
        self.data = data
        self.exists = data is not None
        self.state_hash: str | None = None
        self.content_hash: str | None = None
        if data is not None:
            self.state_hash = _state_hash_of_bytes(data)
            self.content_hash = self.state_hash or _bytes_hash(data)


def _state_hash_of_bytes(data: bytes) -> str | None:
    """:func:`compute_state_hash` of ``data`` parsed, or None if it is no JSON object."""
    try:
        parsed: Any = json.loads(data.decode("utf-8"))
    except ValueError:  # JSONDecodeError and UnicodeDecodeError both subclass it
        return None
    return compute_state_hash(parsed) if isinstance(parsed, dict) else None


def _bytes_hash(data: bytes) -> str:
    """Hash of raw bytes, for a file that does not parse as a state document.

    A distinct prefix, so it can never equal a server ``state_hash``: a corrupt
    file still has a hash to pass to ``--expect-hash`` before it is replaced, but
    no response can ever be taken as a duplicate of it.
    """
    return "sha256-bytes:" + hashlib.sha256(data).hexdigest()


def content_hash(data: bytes) -> str:
    """The hash ``--expect-hash`` compares: the state hash, else the bytes hash.

    For a state file this is the server's own hash of it, so the ``result_hash``
    one save prints is the ``--expect-hash`` the next one passes.
    """
    return _state_hash_of_bytes(data) or _bytes_hash(data)


def _read_destination(path: str) -> _Destination:
    """Read the file a save would replace, or raise :class:`_SaveError`."""
    try:
        with open(path, "rb") as handle:
            return _Destination(handle.read())
    except FileNotFoundError:
        return _Destination(None)
    except OSError as exc:
        raise _SaveError(
            EXIT_LOCAL_IO,
            f"cannot read state file {path!r}: {exc}",
            f"Check that {path!r} is readable.",
            source="state file",
        ) from exc


def _write_temp(target: str, data: bytes) -> str:
    """Write ``data`` to a new uniquely named file beside ``target``; return its path.

    Unique, so two saves of one file never write through the same temporary path,
    and in the same directory, so the ``os.replace`` that installs it stays on one
    filesystem and is atomic. The file is removed again if the write fails.
    """
    directory = os.path.dirname(os.path.abspath(target))
    fd, tmp_path = tempfile.mkstemp(
        dir=directory, prefix="." + os.path.basename(target) + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        _remove_quietly(tmp_path)
        raise
    return tmp_path


def _remove_quietly(path: str) -> None:
    """Delete ``path`` if it exists; a cleanup failure must not mask the real error."""
    with contextlib.suppress(OSError):
        os.unlink(path)


def _replace_with(target: str, data: bytes) -> None:
    """Atomically make ``target`` hold ``data``, through a unique temporary file."""
    tmp_path = _write_temp(target, data)
    try:
        os.replace(tmp_path, target)
    finally:
        _remove_quietly(tmp_path)


def _acquire_lock(fd: int) -> bool:
    """Take an exclusive lock on ``fd``, blocking; False if the platform has none."""
    if sys.platform == "win32":  # pragma: no cover - exercised only on Windows
        import msvcrt

        # LK_LOCK retries for about ten seconds, then raises OSError.
        msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        return True
    try:
        import fcntl
    except ImportError:
        return False
    fcntl.flock(fd, fcntl.LOCK_EX)
    return True


def _release_lock(fd: int) -> None:
    """Release :func:`_acquire_lock`'s lock. Closing the fd releases ``flock``."""
    if sys.platform == "win32":  # pragma: no cover - exercised only on Windows
        import msvcrt

        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


@contextlib.contextmanager
def _file_lock(path: str, warnings: list[Any]) -> Generator[None, None, None]:
    """Hold an exclusive lock on ``path`` for the duration of the block.

    The lock is taken on a ``<path>.lock`` sidecar, not on ``path`` itself:
    ``os.replace`` swaps in a new inode, so a lock held on the old one would guard
    nothing for the next writer. The sidecar is left in place — deleting it would
    let a waiter lock an unlinked inode while a newcomer locks a fresh one. Where
    the platform offers no lock, the save goes ahead and says so in ``warnings``.
    """
    fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        locked = _acquire_lock(fd)
        if not locked:
            warnings.append(
                f"no file locking on this platform; {path} was saved without a lock, "
                "so a concurrent save could go undetected"
            )
        try:
            yield
        finally:
            if locked:
                _release_lock(fd)
    finally:
        os.close(fd)


def _pending_path(path: str) -> str:
    return path + ".pending.json"


def _stale_write(
    path: str,
    expected: str | None,
    found: _Destination,
    response: dict[str, Any],
    keep_pending: bool,
) -> _SaveError:
    """Build the stale-write error, first saving ``response`` beside the file.

    ``expected`` is the ``--expect-hash`` (None for a create, which expected no
    file). The pending copy is what lets the user see what the lost edit was; it is
    never applied automatically, because it was computed against an older file.
    """
    pending: str | None = None
    if keep_pending:
        pending = _pending_path(path)
        try:
            _replace_with(
                pending, (json.dumps(response, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            )
        except OSError:
            pending = None
    if expected is None:
        what = f"{path!r} was created by someone else after this save began"
    elif not found.exists:
        what = f"{path!r} was deleted after its hash was recorded"
    else:
        what = f"{path!r} changed after its hash was recorded"
    kept = f"The server's response was kept in {pending!r}. " if pending else ""
    return _SaveError(
        EXIT_HASH_MISMATCH,
        f"stale write: {what} (expected {expected}, found {found.content_hash}). "
        "The file was left untouched.",
        f"{kept}This edit was made against an older version of the file and must be "
        "reapplied: re-read the state file, record its hash, redo the manage_state "
        "call against it, and save that new response. Do not write the state file "
        "directly, and do not copy the pending response over it.",
        pointer="",
        source="state file",
        details={"expected": expected, "found": found.content_hash, "pending": pending},
        error="stale_write",
    )


def _check_fresh(
    path: str,
    expected: str | None,
    current: _Destination,
    response: dict[str, Any],
    keep_pending: bool,
) -> None:
    """Raise a stale write unless ``current`` is the file the edit was made against.

    With ``--expect-hash`` the file must still exist and still have that hash; with
    none (a create) it must still be absent.
    """
    if expected is None:
        if current.exists:
            raise _stale_write(path, expected, current, response, keep_pending)
        return
    if current.content_hash != expected:
        raise _stale_write(path, expected, current, response, keep_pending)


def _install_new(tmp_path: str, out_path: str) -> bool:
    """Put ``tmp_path`` at ``out_path`` only if nothing is there; False if something is.

    ``os.link`` is the exclusive create: it fails if the name exists, and the file
    it creates is already complete. Where a filesystem has no hard links, an
    ``O_EXCL`` create claims the name and a replace fills it.
    """
    try:
        os.link(tmp_path, out_path)
        return True
    except FileExistsError:
        return False
    except OSError:
        pass
    try:
        os.close(os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644))
    except FileExistsError:
        return False
    try:
        os.replace(tmp_path, out_path)
    except BaseException:
        # The rename did not happen, so out_path is still this call's empty
        # placeholder (other saves are held off by the lock). Left in place, the
        # next save would take it for an existing, corrupt state file. A hard kill
        # between the create and the replace still leaves it: the stdlib has no
        # rename-without-replace to close that window.
        _remove_quietly(out_path)
        raise
    return True


def _install(
    document: dict[str, Any],
    out_path: str,
    expected: str | None,
    result_hash: str,
    response: dict[str, Any],
    warnings: list[Any],
) -> tuple[bool, _Destination]:
    """Write ``document`` to ``out_path`` if the file is still the one edited.

    Under the per-file lock: re-read the file; if it already holds the result
    (a duplicate delivery), write nothing; otherwise check it is the file the edit
    was made against, keep it as ``<file>.bak``, and replace it through a unique
    temporary file. Returns whether anything was written, and the file as found.

    Raises:
        _SaveError: a stale write, or a local I/O failure; either way the file is
            unchanged.
    """
    data = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        with _file_lock(out_path, warnings):
            current = _read_destination(out_path)
            if current.state_hash == result_hash:
                return False, current
            _check_fresh(out_path, expected, current, response, keep_pending=True)
            tmp_path = _write_temp(out_path, data)
            try:
                if current.data is None:
                    if not _install_new(tmp_path, out_path):
                        raise _stale_write(
                            out_path, expected, _read_destination(out_path), response, True
                        )
                else:
                    _replace_with(out_path + ".bak", current.data)
                    os.replace(tmp_path, out_path)
            finally:
                _remove_quietly(tmp_path)
    except OSError as exc:
        raise _SaveError(
            EXIT_LOCAL_IO,
            f"cannot write state file {out_path!r}: {exc}",
            "Check that the directory exists and is writable; the previous file is "
            "unchanged. " + _DO_NOT_HAND_WRITE,
            source="state file",
        ) from exc
    return True, current


def _file_server_prefix() -> str:
    """The URL every accepted https download must start with: ``<base>/files/``."""
    base = os.environ.get(_FILE_SERVER_ENV, "")
    if not base:
        try:
            with open(_MCP_CONFIG, encoding="utf-8") as handle:
                configured: Any = json.load(handle)
            url = configured["mcpServers"]["finplan"]["url"]
            parsed = urllib.parse.urlsplit(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
        except (OSError, ValueError, KeyError, TypeError):
            base = _DEFAULT_FILE_SERVER
    return base.rstrip("/") + "/files/"


def _rejected_url(url: str, why: str) -> _SaveError:
    return _SaveError(
        EXIT_VALIDATION,
        f"--from-url {url!r} is not a FinPlan download: {why}",
        "Pass the urls.data value from the FinPlan tool response, unedited. Do not "
        "download the document some other way and save that instead. " + _DO_NOT_HAND_WRITE,
        pointer="/urls/data",
        source="response",
        details={"found": url},
    )


def _download_source(url: str) -> tuple[str, str]:
    """Check ``url`` is one of FinPlan's own downloads; return ``(kind, target)``.

    ``kind`` is ``"https"`` (``target`` is the URL) or ``"file"`` (``target`` is the
    resolved local path). The hash proves the bytes arrived intact, not where they
    came from, and both the URL and the hash come from the model, so the source is
    pinned instead: an https URL under the FinPlan server's ``/files/``, or a
    ``file://`` path that resolves, symlinks followed, inside the local server's
    download directory. Anything else would let a model install a file it wrote and
    hashed itself, which is the hand-write the plugin's hook exists to stop.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme == "https":
        prefix = _file_server_prefix()
        if not url.startswith(prefix) or parsed.query or parsed.fragment:
            raise _rejected_url(url, f"downloads come from {prefix}")
        # A dot-segment would climb out of /files/ on the server: refuse it here,
        # percent-encoded or not, rather than trust the server to normalise it.
        path = urllib.parse.unquote(parsed.path).replace("\\", "/")
        if "/../" in path or path.endswith("/.."):
            raise _rejected_url(url, "the path climbs out of /files/")
        return "https", url
    if parsed.scheme == "file":
        if parsed.netloc not in ("", "localhost"):
            raise _rejected_url(url, "a file:// URL must name a local path")
        data_dir = os.path.realpath(os.environ.get(_DATA_DIR_ENV) or _DEFAULT_DATA_DIR)
        raw_path = urllib.request.url2pathname(parsed.path)
        # A percent-encoded NUL decodes to a real one, which realpath and open reject
        # with ValueError rather than OSError.
        if "\x00" in raw_path:
            raise _rejected_url(url, "the path is not a valid local path")
        path = os.path.realpath(raw_path)
        if os.path.commonpath([path, data_dir]) != data_dir:
            raise _rejected_url(url, f"local downloads live under {data_dir}")
        return "file", path
    raise _rejected_url(url, "only https and file:// downloads are accepted")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects: a redirect could lead off the host that was checked."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _fetch(url: str) -> bytes:
    """Download ``url`` (already checked by :func:`_download_source`), size-capped."""
    opener = urllib.request.build_opener(_NoRedirect)
    hint_retry = (
        "Nothing was written. A download link lasts about an hour: if it has expired, "
        "redo the tool call and save its new response. " + _DO_NOT_HAND_WRITE
    )
    try:
        with opener.open(url, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as reply:
            data: bytes = reply.read(_MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise _SaveError(
            EXIT_SERVER,
            f"the server answered the download with HTTP {exc.code} ({exc.reason})",
            hint_retry,
            source="response",
            details={"found": exc.code},
        ) from exc
    # http.client.HTTPException is not an OSError: a chunked body cut off mid-chunk
    # (IncompleteRead) or a malformed status line (BadStatusLine) raises it.
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        hint = (
            "Nothing was written. Check the network connection and retry the same "
            "save; if the link has expired, redo the tool call. "
        )
        # A sandbox's filtering proxy refuses the CONNECT for a host it does not allow.
        if "Tunnel connection failed" in str(reason):
            hint = (
                "Nothing was written. A sandbox or proxy refused the connection to the "
                "FinPlan server, so retrying will not help. Redo the tool call with "
                "full_document='inline' and save that response instead, and tell the "
                "user that allowing mcp.finplan.tools in the sandbox's network settings "
                "makes later saves cheaper. "
            )
        raise _SaveError(
            EXIT_NETWORK,
            f"cannot download {url!r}: {reason}",
            hint + _DO_NOT_HAND_WRITE,
            source="response",
        ) from exc
    return data


def _download_document(url: str, kind: str, target: str, state_hash: str) -> dict[str, Any]:
    """Fetch the document at ``url`` as a full-document response carrying ``state_hash``.

    ``kind`` and ``target`` are :func:`_download_source`'s verdict on ``url``. The
    result has the shape of an inline full-document response, so the rest of
    ``save`` treats both alike: the hash check, the stale-write guard and the
    duplicate check do not know where the document came from.
    """
    if kind == "https":
        data = _fetch(target)
    else:
        try:
            with open(target, "rb") as handle:
                data = handle.read(_MAX_DOWNLOAD_BYTES + 1)
        except (OSError, ValueError) as exc:
            raise _SaveError(
                EXIT_LOCAL_IO,
                f"cannot read download {target!r}: {exc}",
                "Nothing was written. A local download is removed after about an hour: "
                "redo the tool call and save its new response.",
                source="response",
            ) from exc
    if len(data) > _MAX_DOWNLOAD_BYTES:
        raise _SaveError(
            EXIT_VALIDATION,
            f"the download is larger than {_MAX_DOWNLOAD_BYTES} bytes, so it is not a "
            "FinPlan state document",
            "Pass the urls.data value from the FinPlan tool response, unedited.",
            pointer="/urls/data",
            source="response",
        )
    try:
        parsed: Any = json.loads(data.decode("utf-8"))
    except ValueError as exc:
        raise _SaveError(
            EXIT_VALIDATION,
            f"the download at {url!r} is not valid JSON: {exc}",
            "Nothing was written. Redo the tool call and save its new response.",
            pointer="",
            source="response",
        ) from exc
    if not isinstance(parsed, dict):
        raise _SaveError(
            EXIT_VALIDATION,
            f"the download at {url!r} is not a JSON object",
            "Nothing was written. Pass the urls.data of a state document.",
            pointer="",
            source="response",
        )
    response = dict(parsed)
    # A state document has no top-level `changed`; forcing the key out keeps a
    # download on the full-document path, never the delta path.
    response.pop("changed", None)
    response["state_hash"] = state_hash
    return response


def _load_response(args: argparse.Namespace, current: _Destination) -> dict[str, Any] | None:
    """The response to save, or None when ``--from-url`` names a result already on disk.

    ``--from-url`` requires ``--state-hash`` (the response's ``state_hash``, which a
    download response also carries as ``content_hash``), and ``--state-hash`` means
    nothing without it. The URL is checked first, always. A download whose result
    the file already holds is then not fetched: the retry of a save that succeeded
    must succeed even once the link has expired.
    """
    if args.from_url is None:
        if args.state_hash is not None:
            raise _SaveError(
                EXIT_VALIDATION,
                "--state-hash goes with --from-url; a --response carries its own state_hash",
                "Drop --state-hash, or pass the download's URL as --from-url.",
                source="response",
            )
        return _load_json_object(args.response, "response")
    if not args.state_hash:
        raise _SaveError(
            EXIT_VALIDATION,
            "--from-url needs --state-hash",
            "Pass the response's state_hash (equal to its content_hash) as --state-hash.",
            pointer="/state_hash",
            source="response",
        )
    kind, target = _download_source(args.from_url)
    if current.state_hash == args.state_hash:
        return None
    return _download_document(args.from_url, kind, target, args.state_hash)


def _save(args: argparse.Namespace) -> dict[str, Any]:
    """Run ``save`` and return its envelope, or raise :class:`_SaveError`."""
    out_path = args.out if args.out else args.state
    current = _read_destination(out_path)
    loaded = _load_response(args, current)
    if loaded is None:
        return _duplicate_envelope({"state_hash": args.state_hash}, out_path, current, [])
    response = loaded
    warnings: list[Any] = []
    response_warnings = response.get("warnings")
    if isinstance(response_warnings, list):
        warnings.extend(response_warnings)

    # An empty value is no hash at all: `--expect-hash "$(finplan.py hash F)"` on a
    # file that does not exist yet passes "", and that is a create, not a deletion.
    expected: str | None = args.expect_hash or None

    # A response whose result the file already holds was delivered before: that
    # is success, and nothing is written. Checked before the delta is applied,
    # because applying a delta twice is what it must never do, and before the
    # --expect-hash requirement, because a retried create arrives without one.
    response_hash = response.get("state_hash")
    if isinstance(response_hash, str) and current.state_hash == response_hash:
        return _duplicate_envelope(response, out_path, current, warnings)

    if current.exists and expected is None and not args.dry_run:
        raise _SaveError(
            EXIT_VALIDATION,
            f"{out_path!r} exists, so save needs --expect-hash",
            f"Before the manage_state call, record the file's hash with "
            f"`finplan.py hash {out_path}` (or take the result_hash the last save "
            "printed), and pass it as --expect-hash. " + _DO_NOT_HAND_WRITE,
            pointer="",
            source="state file",
        )

    # Checked before the delta is read, so an edit made against an older file is
    # reported as the stale write it is, not as whatever its replay against the
    # newer file happens to break.
    # A dry run may leave --expect-hash off: it writes nothing, so there is no
    # write to guard, but given one it reports a stale response as a real run would.
    if not (args.dry_run and expected is None):
        _check_fresh(out_path, expected, current, response, keep_pending=not args.dry_run)

    if "changed" not in response:
        # Full / migrated document (create, return_full_state, migrated): the
        # response *is* the new state, once its transient metadata is stripped below.
        document: dict[str, Any] = dict(response)
        input_hash = current.state_hash
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

    data: dict[str, Any] = {
        "action": response.get("action"),
        "change": summary["change"],
        "section": summary["section"],
        "item_id": summary["item_id"],
        "path": out_path,
        "written": False,
    }
    if args.dry_run:
        data["item"] = summary["item"]
    else:
        # Nothing is defaulted in after verification: `last_updated` and
        # `schema_fingerprint` are both declared UserState fields, so every document
        # the server hashes already carries them. Filling them in here would be the
        # one path by which the bytes on disk could differ from the bytes verified.
        written, found = _install(document, out_path, expected, expected_hash, response, warnings)
        if not written:
            # Another save delivered this same result while this one was running.
            return _duplicate_envelope(response, out_path, found, warnings)
        data["written"] = True
    return {
        "data": data,
        "metadata": {
            "input_hash": input_hash,
            "result_hash": expected_hash,
            "warnings": warnings,
        },
    }


def _duplicate_envelope(
    response: dict[str, Any], out_path: str, current: _Destination, warnings: list[Any]
) -> dict[str, Any]:
    """The success envelope for a response whose result the file already holds."""
    return {
        "data": {
            "action": response.get("action"),
            "change": "unchanged",
            "section": None,
            "item_id": None,
            "path": out_path,
            "written": False,
            "duplicate": True,
        },
        "metadata": {
            "input_hash": current.state_hash,
            "result_hash": response.get("state_hash"),
            "warnings": warnings,
        },
    }


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

    A verified response can still be stale: computed against a file that has
    changed since. So when the destination exists, ``--expect-hash`` must give its
    hash as recorded before the server call, and the file is replaced only if it
    still has that hash; when it does not exist, it must still be absent when the
    new file is installed. Both checks run under a per-file lock. A stale response
    leaves the file untouched and is kept beside it as ``<file>.pending.json``; a
    response whose result the file already holds is a duplicate delivery and
    succeeds without writing. A successful write keeps the replaced file as
    ``<file>.bak``.

    ``--from-url`` takes the place of ``--response`` when a tool served the full
    document as a ``urls.data`` download: the document is fetched only from
    FinPlan's own download locations (:func:`_download_source`), checked against
    ``--state-hash``, and saved exactly as an inline full document would be.

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


def _cmd_hash(args: argparse.Namespace) -> int:
    """Print a file's content hash: the value ``save --expect-hash`` compares.

    For a state document this is the server's ``state_hash`` of it; for a file that
    is not a JSON object, a hash of its bytes (``sha256-bytes:…``), so even a
    corrupt file can be replaced deliberately.
    """
    try:
        with open(args.file, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        print(f"error: cannot read {args.file!r}: {exc}", file=sys.stderr)
        return EXIT_LOCAL_IO
    print(content_hash(data))
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
            "stdout ({data, metadata}); errors go to stderr as JSON.\n\n"
            "If the file exists, pass --expect-hash with its hash from before the\n"
            "manage_state call (`finplan.py hash FILE`, or the last save's result_hash).\n"
            "If it changed since, nothing is written: the response is kept in\n"
            "FILE.pending.json and the edit must be reapplied. A successful write keeps\n"
            "the previous file as FILE.bak.\n\n"
            "When the response carries urls.data instead of the document, pass\n"
            "--from-url URL --state-hash HASH in place of --response: the document is\n"
            "downloaded (only from the FinPlan server, or from the local server's\n"
            "download directory), checked against HASH, and saved the same way."
        ),
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_save.add_argument("--state", required=True, help="path to the local state.json")
    source = p_save.add_mutually_exclusive_group(required=True)
    source.add_argument("--response", help="manage_state response file, or - for stdin")
    source.add_argument(
        "--from-url",
        default=None,
        help="the response's urls.data: download the full document from it instead",
    )
    p_save.add_argument(
        "--state-hash",
        default=None,
        help="with --from-url: the response's state_hash (its content_hash)",
    )
    p_save.add_argument("--out", default=None, help="write here instead of --state")
    p_save.add_argument(
        "--expect-hash",
        default=None,
        help="the destination's hash before the server call; required when it exists",
    )
    p_save.add_argument(
        "--dry-run",
        action="store_true",
        help="verify and print the item that would change; write nothing",
    )
    p_save.set_defaults(func=_cmd_save)

    p_hash = subparsers.add_parser(
        "hash", help="print a state file's content hash, for save --expect-hash"
    )
    p_hash.add_argument("file", help="the state file")
    p_hash.set_defaults(func=_cmd_hash)

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
