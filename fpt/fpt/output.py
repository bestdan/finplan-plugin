"""The one output contract every fpt command follows, for people and agents alike.

Success is one JSON envelope on standard output and nothing else there: ``data`` holds the
result, ``metadata`` the facts about it. Failure is one JSON object on standard error and
an exit code from :mod:`fpt.exit_codes`. Detecting an agent changes neither (see
:mod:`fpt.client`): the same command prints the same bytes for everyone.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from typing import Any, TextIO

from fpt.exit_codes import ExitCode


def envelope(
    data: Any,
    *,
    input_hash: str | None = None,
    result_hash: str | None = None,
    schema_fingerprint: str | None = None,
    out: str | None = None,
    truncated: bool = False,
    next_cursor: str | None = None,
    next_action: str | None = None,
    warnings: Sequence[Any] = (),
) -> dict[str, Any]:
    """Build the success envelope.

    Every ``metadata`` key is always present, ``null`` when it does not apply, so a caller
    reads the same shape from every command.

    Args:
        data: The result. When the full result went to a file, a summary, with ``out``
            naming the file.
        input_hash: Content hash of the state the command read.
        result_hash: Content hash of the state it produced.
        schema_fingerprint: The state schema the result conforms to.
        out: Path of the file holding the full result, when it is not inline.
        truncated: Whether ``data`` is a first page of a longer list.
        next_cursor: The value to pass to get the next page, when ``truncated``.
        next_action: The command to run next, written out in full.
        warnings: Non-fatal notes, including the server's ``Deprecation``/``Sunset``.
    """
    return {
        "data": data,
        "metadata": {
            "input_hash": input_hash,
            "result_hash": result_hash,
            "schema_fingerprint": schema_fingerprint,
            "out": out,
            "truncated": truncated,
            "next_cursor": next_cursor,
            "next_action": next_action,
            "warnings": list(warnings),
        },
    }


def emit(result: dict[str, Any], stream: TextIO | None = None) -> int:
    """Print an envelope as one line of JSON on standard output; return the success code."""
    target = stream if stream is not None else sys.stdout
    target.write(json.dumps(result, ensure_ascii=False) + "\n")
    return ExitCode.OK


class FptError(Exception):
    """A command failure, reported on standard error as one JSON object.

    ``pointer`` is a JSON Pointer (RFC 6901) into the document named by ``source``,
    following RFC 9457's ``errors[].pointer``. ``hint`` says what to change and, where an
    obvious wrong move exists, names it as the thing not to do: a warning that names the
    failing approach is followed far more often than a tip. ``error`` overrides the name the
    code carries, for a code that covers two failures recovered from differently (3 is a
    ``hash_mismatch`` or a ``stale_write``).
    """

    def __init__(
        self,
        exit_code: ExitCode,
        message: str,
        hint: str,
        *,
        pointer: str | None = None,
        source: str | None = None,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.error = error or exit_code.error_name
        self.message = message
        self.hint = hint
        self.pointer = pointer
        self.source = source
        self.details = details or {}

    def to_json(self) -> dict[str, Any]:
        """The stderr payload: what failed, where, and what to change."""
        payload: dict[str, Any] = {
            "error": self.error,
            "exit_code": int(self.exit_code),
            "message": self.message,
            "source": self.source,
            "pointer": self.pointer,
            "hint": self.hint,
        }
        payload.update(self.details)
        return payload


def emit_error(error: FptError, stream: TextIO | None = None) -> int:
    """Print an error as one line of JSON on standard error; return its exit code."""
    target = stream if stream is not None else sys.stderr
    target.write(json.dumps(error.to_json(), ensure_ascii=False) + "\n")
    return int(error.exit_code)
