"""The ``fpt`` command: argument parsing and dispatch.

Each command registers itself through a function in :data:`COMMANDS`, which adds its
subparser and sets ``func``; ``func`` takes the parsed arguments and returns an exit
code. The commands are in :mod:`fpt.commands` and :mod:`fpt.skills`; with no command
given, fpt reports a validation error.

``--help`` and ``--version`` are the two outputs that are not JSON: help is for people,
and ``fpt <version>`` is the one line the plugin compares against the range it supports.
Everything else follows :mod:`fpt.output`.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from typing import Any, NoReturn

from fpt import __version__
from fpt.auth import register_auth
from fpt.commands import register_hash, register_save
from fpt.exit_codes import EXIT_CODES_HELP, ExitCode
from fpt.output import FptError, emit_error
from fpt.skills import register_skills


class _Parser(argparse.ArgumentParser):
    """An ``ArgumentParser`` whose usage errors follow fpt's error contract.

    argparse prints a usage line to stderr and exits 2. fpt's 2 is validation too, but its
    stderr must be one JSON object a caller can parse, so the error is raised as an
    :class:`FptError` instead and reported by :func:`main`.
    """

    def error(self, message: str) -> NoReturn:
        raise FptError(
            ExitCode.VALIDATION,
            f"{self.prog}: {message}",
            f"Run `{self.prog} --help` for the arguments it takes.",
            source="arguments",
        )


# Each command's registration function, called with the subparsers action (typed Any
# because argparse's _SubParsersAction is private).
COMMANDS: list[Callable[[Any], None]] = [
    register_save,
    register_hash,
    register_skills,
    register_auth,
]


def build_parser() -> argparse.ArgumentParser:
    """The ``fpt`` parser, with every command in :data:`COMMANDS` registered."""
    parser = _Parser(
        prog="fpt",
        description="A thin local client for FinPlan that keeps state and bulk data "
        "out of the LLM. Every command prints one JSON envelope on stdout.",
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"fpt {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>", parser_class=_Parser)
    for register in COMMANDS:
        register(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv`` and run the chosen command; return the exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        func: Any = getattr(args, "func", None)
        if func is None:
            raise FptError(
                ExitCode.VALIDATION,
                "fpt: no command given",
                "Run `fpt --help` for the commands it has, or `fpt --version`.",
                source="arguments",
            )
        result: int = func(args)
        return result
    except FptError as error:
        return emit_error(error)
