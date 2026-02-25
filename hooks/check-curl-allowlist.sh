#!/usr/bin/env bash
# PostToolUse hook: After first MCP finplan tool call, check if the user has
# allowlisted curl for the FinPlan file server. If not, suggest the one-liner.

SETTINGS="$HOME/.claude/settings.json"
MARKER="$HOME/.claude/.finplan-curl-hint-shown"
PATTERN="mcp.finplan.prethink.io"

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
    "additionalContext": "TIP: FinPlan tools download result files via curl. To avoid repeated approval prompts, run:\n\n  claude settings add allowedTools 'Bash(curl*mcp.finplan.prethink.io*)'\n\nThis allowlists curl only for the FinPlan file server."
  }
}
EOF
