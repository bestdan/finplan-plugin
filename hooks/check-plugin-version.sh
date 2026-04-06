#!/usr/bin/env bash
# PostToolUse hook: On first FinPlan MCP tool call per session, check whether
# the plugin is outdated relative to the server's minimum required version.
#
# The MCP server's root endpoint (/) returns JSON including:
#   { "version": "0.1.0", "min_plugin_version": "1.0.2" }
#
# If min_plugin_version is present and the installed plugin version is older,
# surface a one-time hint to update.

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
PLUGIN_JSON="$PLUGIN_ROOT/.claude-plugin/plugin.json"
MARKER="/tmp/.finplan-version-check-$$"
SERVER_URL="https://mcp.finplan.prethink.io"

# --- guard: only check once per session ---
# Use parent PID as a rough session identifier so the check runs once per
# Claude Code process, not once per tool call.
SESSION_MARKER="/tmp/.finplan-version-check-$(ps -o ppid= $$ 2>/dev/null | tr -d ' ')"
[ -f "$SESSION_MARKER" ] && exit 0

# Read installed plugin version
if [ ! -f "$PLUGIN_JSON" ]; then
  exit 0
fi
PLUGIN_VERSION=$(python3 -c "
import json, sys
with open('$PLUGIN_JSON') as f:
    print(json.load(f).get('version', '0.0.0'))
" 2>/dev/null || echo "0.0.0")

# Mark as checked regardless of outcome
touch "$SESSION_MARKER"

# Fetch server info (short timeout to avoid blocking)
SERVER_INFO=$(curl -s --max-time 3 "$SERVER_URL/" 2>/dev/null) || exit 0

# Extract min_plugin_version (exit silently if the field doesn't exist yet)
MIN_PLUGIN_VERSION=$(echo "$SERVER_INFO" | python3 -c "
import json, sys
data = json.load(sys.stdin)
v = data.get('min_plugin_version')
if v:
    print(v)
else:
    sys.exit(1)
" 2>/dev/null) || exit 0

# Compare versions: is PLUGIN_VERSION < MIN_PLUGIN_VERSION?
IS_OUTDATED=$(python3 -c "
import sys
try:
    from packaging.version import Version
    outdated = Version('$PLUGIN_VERSION') < Version('$MIN_PLUGIN_VERSION')
except Exception:
    # packaging not installed — fall back to simple tuple comparison
    def parse(v):
        base = v.split('-')[0]
        return tuple(int(x) for x in base.split('.'))
    outdated = parse('$PLUGIN_VERSION') < parse('$MIN_PLUGIN_VERSION')
print('yes' if outdated else 'no')
" 2>/dev/null || echo "no")

if [ "$IS_OUTDATED" = "yes" ]; then
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "UPDATE AVAILABLE: Your FinPlan plugin (v${PLUGIN_VERSION}) is older than the minimum version required by the server (v${MIN_PLUGIN_VERSION}). Some tools may not work correctly.\n\nTo update:\n  claude plugin update finplan\n\nOr enable auto-updates:\n  /plugin → Marketplaces → finplan-plugin → Enable auto-update"
  }
}
EOF
fi
