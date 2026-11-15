"""``python -m fpt``, the same as the ``fpt`` command."""

import sys

from fpt.main import main

# Guarded because pytest's --doctest-modules imports every module, this one included.
if __name__ == "__main__":  # pragma: no cover - exercised by test_main's subprocess run
    sys.exit(main())
