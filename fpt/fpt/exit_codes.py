"""The exit codes every fpt command uses, one table for all of them.

They are the same codes, with the same names, as the plugin's ``finplan.py``, so a
caller branches on either the same way without parsing text. ``tests/test_fpt_exit_codes.py`` at the repo root fails if the two tables drift.
1 stays what Python itself exits with on an uncaught error.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """An fpt exit code. ``error_name`` is the ``error`` field of the stderr JSON."""

    OK = 0
    INTERNAL = 1
    VALIDATION = 2
    HASH_MISMATCH = 3
    LOCAL_IO = 4
    AUTH = 5
    NETWORK = 6
    SERVER = 7

    @property
    def error_name(self) -> str:
        """The lowercase name an error payload carries, e.g. ``hash_mismatch``."""
        return self.name.lower()


EXIT_CODES_HELP = """\
exit codes (shared with the plugin's finplan.py):
  0  success
  1  internal error (an uncaught exception; a bug)
  2  validation: bad arguments or input
  3  hash mismatch or stale write: nothing was written
  4  local I/O: a file could not be read or written
  5  authentication: not signed in, or the key was refused
  6  network: the server could not be reached
  7  server error: the server answered with an error
"""
