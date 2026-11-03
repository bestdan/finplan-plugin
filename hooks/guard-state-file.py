#!/usr/bin/env python3
"""PreToolUse hook: deny Write and Edit on a FinPlan state file.

With the plugin installed, the model never writes ``*finplan_state.json`` itself.
Every write goes through ``finplan.py save``, which applies the server's response
and checks it against the server's ``state_hash``. A hand-written file drops fields
the model did not retype.

Reads the hook payload on stdin. For a Write or Edit whose ``file_path`` names a
state file (basename ``finplan_state.json`` or ``<name>_finplan_state.json``), prints
a ``permissionDecision: deny`` with what to do instead. Anything else, including
``<file>.pending.json`` and ``<file>.bak``, passes with no output. A payload it cannot
parse passes too: this hook guards a convention, and a broken hook must not block
every write.

Shell writes (``>``, ``tee``, ``cp``) are not hooked; the denial message and the
skill text tell the model not to use them.

Stdlib only, Python 3.9+: it runs on the user's machine.
"""

from __future__ import annotations

import json
import os
import sys
from typing import cast

STATE_SUFFIX = "finplan_state.json"
GUARDED_TOOLS = frozenset({"Write", "Edit"})

REASON = (
    "FinPlan state files are written only by finplan.py, never with Write or Edit. "
    "To change the plan, call manage_state, then run /finplan:save-state, which saves "
    "the response with `finplan.py save` and checks it against the server's state_hash. "
    "Do not write the file through the shell either: no `>` redirect, `jq ... > file`, "
    "`cp`, `mv`, `tee` or `python3 -c`. A redirect onto the file being read empties it "
    "before jq runs. If the file is malformed, tell the user rather than repairing it "
    "by hand."
)


def is_state_file(path: str) -> bool:
    """True when ``path``'s basename is a FinPlan state file."""
    name = os.path.basename(path)
    return name == STATE_SUFFIX or name.endswith("_" + STATE_SUFFIX)


def decide(payload: object) -> dict[str, object] | None:
    """The hook's output for ``payload``, or None to let the call through."""
    if not isinstance(payload, dict):
        return None
    fields = cast(dict[str, object], payload)
    if fields.get("tool_name") not in GUARDED_TOOLS:
        return None
    tool_input = fields.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    path = cast(dict[str, object], tool_input).get("file_path")
    if not isinstance(path, str) or not is_state_file(path):
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON,
        }
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    output = decide(payload)
    if output is not None:
        json.dump(output, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
