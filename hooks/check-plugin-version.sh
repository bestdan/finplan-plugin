#!/usr/bin/env bash
# PostToolUse hook: On first FinPlan MCP tool call per session, check whether the
# installed plugin is out of date, and if so surface a one-time hint to update.
#
# Two independent signals, each optional (a missing one is simply skipped):
#   1. latest  — the newest published version, read from the public marketplace
#                repo's plugin.json (authoritative, CI-bumped on every release).
#                Read from the *channel* the install came from (see below), so a
#                dev build is compared against its own branch, not stable main.
#   2. min     — a hard compatibility floor, read from the MCP server's / endpoint
#                ({ "min_plugin_version": "x.y.z" }). Only set on breaking releases;
#                the server omits it otherwise, so today this stays unused.
#
# Tiering:
#   installed < min          -> strong "update required" (some tools may not work)
#   dev channel, version !=  -> gentle "update available" (see below)
#   installed < latest       -> gentle "update available"
#   otherwise                -> say nothing
#
# Channels: CI stamps the finplan-plugin branch it synced to into plugin.json as
# `channel` ("main" for stable, the dev branch name otherwise). Semver cannot
# order two -dev.<sha> pre-releases, but a dev branch only ever receives newer
# syncs and every sync rewrites the sha, so on a dev channel a version string
# that differs from the channel's published one means the install is behind.
# An install with no `channel` (a source checkout, or a --plugin-dir install)
# reads as "main" and keeps today's semver-only behavior.
#
# The hook never blocks or errors a real tool call: any missing field, network
# failure, or parse error degrades to silence (exit 0).

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
PLUGIN_JSON="$PLUGIN_ROOT/.claude-plugin/plugin.json"
SERVER_URL="https://mcp.finplan.tools"
REPO_RAW_BASE="https://raw.githubusercontent.com/bestdan/finplan-plugin"

# --- guard: only check once per session ---
# Use parent PID as a rough session identifier so the check runs once per
# Claude Code process, not once per tool call. Marker lives under TMPDIR (a
# stable per-session temp dir) so the check stays once-per-session in real use
# and a test can isolate its markers by pointing TMPDIR at a scratch dir.
TMP_DIR="${TMPDIR:-/tmp}"
SESSION_MARKER="${TMP_DIR%/}/.finplan-version-check-$(ps -o ppid= $$ 2>/dev/null | tr -d ' ')"
[ -f "$SESSION_MARKER" ] && exit 0

# Read installed plugin version
if [ ! -f "$PLUGIN_JSON" ]; then
  exit 0
fi
PLUGIN_VERSION=$(python3 -c "
import json
with open('$PLUGIN_JSON') as f:
    print(json.load(f).get('version', '0.0.0'))
" 2>/dev/null || echo "0.0.0")

# Publish channel this install came from — CI stamps it on every sync. Absent
# (a source checkout or a --plugin-dir install) reads as "main", which keeps
# today's semver-only behavior for those installs.
PLUGIN_CHANNEL=$(python3 -c "
import json
with open('$PLUGIN_JSON') as f:
    print(json.load(f).get('channel', '') or 'main')
" 2>/dev/null || echo "main")
# The ref segment stays unencoded. raw.githubusercontent.com resolves a slashed
# branch name (feature/foo) against the repo's real refs rather than splitting on
# the first slash — verified 200 on a public repo with such a branch. Percent-
# encoding the slash is unnecessary, and is not the form CI publishes.
REPO_RAW_URL="$REPO_RAW_BASE/$PLUGIN_CHANNEL/.claude-plugin/plugin.json"

# Mark as checked regardless of outcome
touch "$SESSION_MARKER"

# --- gather reference versions (each optional) ---
# .version from a JSON document on stdin, or empty string if absent/unparseable.
_json_field() {
  python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('$1') or '')
except Exception:
    print('')
" 2>/dev/null || echo ""
}

# Fetch both endpoints in parallel so the worst-case first-call delay is one
# timeout (~3s), not the sum of two.
_server_out="${TMP_DIR%/}/.finplan-vc-server-$$"
_repo_out="${TMP_DIR%/}/.finplan-vc-repo-$$"
curl -s --max-time 3 "$SERVER_URL/" >"$_server_out" 2>/dev/null &
_server_pid=$!
curl -s --max-time 3 "$REPO_RAW_URL" >"$_repo_out" 2>/dev/null &
_repo_pid=$!
wait "$_server_pid" "$_repo_pid" 2>/dev/null
SERVER_INFO=$(cat "$_server_out" 2>/dev/null)
REPO_INFO=$(cat "$_repo_out" 2>/dev/null)
rm -f "$_server_out" "$_repo_out"
MIN_PLUGIN_VERSION=$(printf '%s' "$SERVER_INFO" | _json_field min_plugin_version)
LATEST_PLUGIN_VERSION=$(printf '%s' "$REPO_INFO" | _json_field version)

# Nothing to compare against -> stay silent (this is today's behavior).
if [ -z "$MIN_PLUGIN_VERSION" ] && [ -z "$LATEST_PLUGIN_VERSION" ]; then
  exit 0
fi

# "yes" if $1 < $2 (both non-empty), else "no". Empty operands never compare.
_ver_lt() {
  python3 -c "
import sys
a, b = sys.argv[1], sys.argv[2]
if not a or not b:
    print('no'); sys.exit(0)
try:
    from packaging.version import Version
    print('yes' if Version(a) < Version(b) else 'no')
except Exception:
    # packaging not installed — fall back to simple tuple comparison
    def parse(v):
        base = v.split('-')[0].split('+')[0]
        return tuple(int(x) for x in base.split('.'))
    try:
        print('yes' if parse(a) < parse(b) else 'no')
    except Exception:
        print('no')
" "$1" "$2" 2>/dev/null || echo "no"
}

# Emit a PostToolUse additionalContext payload (JSON-escaped via python).
_emit() {
  python3 -c "
import json, sys
print(json.dumps({'hookSpecificOutput': {
    'hookEventName': 'PostToolUse',
    'additionalContext': sys.argv[1],
}}))
" "$1"
}

# Real newlines (not literal "\n"): _emit's json.dumps turns these into proper
# JSON \n escapes. Embedding literal backslash-n here would instead emit \\n and
# render as visible "\n" in the hint.
NL=$'\n'
UPDATE_STEPS="To update:${NL}  claude plugin update finplan   (then restart Claude Code to apply)${NL}${NL}Or enable auto-updates so this happens for you:${NL}  /plugin → Marketplaces → finplan-plugin → Enable auto-update"

if [ "$(_ver_lt "$PLUGIN_VERSION" "$MIN_PLUGIN_VERSION")" = "yes" ]; then
  _emit "UPDATE REQUIRED: Your FinPlan plugin (v${PLUGIN_VERSION}) is older than the minimum version required by the server (v${MIN_PLUGIN_VERSION}). Some tools may not work correctly.${NL}${NL}${UPDATE_STEPS}"
elif [ "$PLUGIN_CHANNEL" != "main" ]; then
  # Dev channel: compare against the same branch, by exact version string. Semver
  # can't order two -dev.<sha> builds, but the branch only ever moves forward and
  # each sync rewrites the sha, so a difference means the channel has moved on. A
  # deleted branch 404s -> LATEST is empty -> silent, as with any fetch failure.
  if [ -n "$LATEST_PLUGIN_VERSION" ] && [ "$PLUGIN_VERSION" != "$LATEST_PLUGIN_VERSION" ]; then
    _emit "UPDATE AVAILABLE: A newer FinPlan plugin dev build is available on the ${PLUGIN_CHANNEL} channel (v${PLUGIN_VERSION} → v${LATEST_PLUGIN_VERSION}).${NL}${NL}${UPDATE_STEPS}"
  fi
elif [ "$(_ver_lt "$PLUGIN_VERSION" "$LATEST_PLUGIN_VERSION")" = "yes" ]; then
  _emit "UPDATE AVAILABLE: A newer FinPlan plugin is available (v${PLUGIN_VERSION} → v${LATEST_PLUGIN_VERSION}).${NL}${NL}${UPDATE_STEPS}"
fi
