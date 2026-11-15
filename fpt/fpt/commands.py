"""The commands fpt runs: ``save`` and ``hash``, registered in :data:`fpt.main.COMMANDS`.

``save`` is :mod:`fpt.save`'s, unchanged, so it prints the same envelope and save errors
as the plugin's ``finplan.py save``. Usage errors differ: fpt reports them as JSON,
``finplan.py`` as argparse's usage text. ``hash`` differs from ``finplan.py hash``, which prints
the bare hash: here it is an envelope, like every fpt command.
"""

from __future__ import annotations

import argparse
from typing import Any

from fpt import save
from fpt.exit_codes import EXIT_CODES_HELP, ExitCode
from fpt.output import FptError, emit, envelope


def register_save(subparsers: Any) -> None:
    """Add ``fpt save``."""
    parser = subparsers.add_parser(
        "save",
        help="merge a manage_state response into a local state file",
        description=save.save_description("fpt"),
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    save.add_save_arguments(parser, "fpt")


def _cmd_hash(args: argparse.Namespace) -> int:
    """Print the file's content hash as ``data.hash``, for ``save --expect-hash``."""
    try:
        with open(args.file, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        raise FptError(
            ExitCode.LOCAL_IO,
            f"cannot read {args.file!r}: {exc}",
            f"Check that {args.file!r} exists and is readable.",
            source="arguments",
        ) from exc
    digest = save.content_hash(data)
    return emit(envelope({"path": args.file, "hash": digest}, input_hash=digest))


def register_hash(subparsers: Any) -> None:
    """Add ``fpt hash``."""
    parser = subparsers.add_parser(
        "hash",
        help="print a state file's content hash, for save --expect-hash",
        description="Print FILE's content hash as data.hash: for a state document, the "
        "server's state_hash of it; for any other file, a hash of its bytes "
        "(sha256-bytes:…). Pass it to `fpt save --expect-hash`.",
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="the state file")
    parser.set_defaults(func=_cmd_hash)
