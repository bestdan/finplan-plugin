"""fpt: a thin local client for FinPlan that keeps state and bulk data out of the LLM.

fpt holds no financial logic. It never imports ``finplan_core`` or ``finplan_mcp``;
``fpt/tests/test_no_engine_import.py`` fails if it does.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

DISTRIBUTION = "finplantools-fpt"

try:
    __version__ = version(DISTRIBUTION)
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled source tree
    __version__ = "0+unknown"

__all__ = ["DISTRIBUTION", "__version__"]
