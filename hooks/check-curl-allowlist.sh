#!/usr/bin/env bash
# PostToolUse hook: After first MCP finplan tool call, check if the user has
# allowlisted curl for the FinPlan file server. If not, suggest the one-liner.

SETTINGS="$HOME/.claude/settings.json"
MARKER="$HOME/.claude/.finplan-curl-hint-shown-finplan-tools-v2"
PATTERN="mcp.finplan.tools"

# Only show once per install (marker file tracks this)
[ -f "$MARKER" ] && exit 0

# Check if the allowlist already covers the domain
if [ -f "$SETTINGS" ] && grep -q "$PATTERN" "$SETTINGS" 2>/dev/null; then
  touch "$MARKER"
  exit 0
fi

# First time seeing a finplan tool call without the allowlist — surface a hint
touch "$MARKER"

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "TIP: FinPlan tools download result files via curl. To avoid repeated approval prompts, add \"Bash(curl*mcp.finplan.tools*)\" to the permissions.allow array in ~/.claude/settings.json (keep existing entries). It allowlists curl only for the FinPlan file server. Adding \"mcp__plugin_finplan_finplan\" there too stops the per-call prompt for FinPlan tools. Offer to make the edit; do not make it without the user's consent."
  }
}
EOF
