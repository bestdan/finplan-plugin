#!/usr/bin/env bash
# Plain-bash tests for check-plugin-version.sh.
#
# Run: bash packages/plugin/hooks/tests/test_check_plugin_version.sh
#
# Stubs `curl` via a PATH shim that returns canned server / and repo plugin.json
# payloads (controlled by FAKE_* env vars), and points the hook at a temp plugin
# root, so the tiering logic can be exercised offline and deterministically.

set -u
HOOK="$(cd "$(dirname "$0")/.." && pwd)/check-plugin-version.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/root/.claude-plugin" "$TMP/bin"

# curl shim: branch on the requested URL; honor FAKE_* knobs.
cat > "$TMP/bin/curl" <<'SHIM'
#!/usr/bin/env bash
url=""
for a in "$@"; do case "$a" in http*) url="$a" ;; esac; done
case "$url" in
  *mcp.finplan.tools*)
    [ -n "${FAKE_SERVER_FAIL:-}" ] && exit 1
    if [ -n "${FAKE_MIN:-}" ]; then
      printf '{"version":"0.1.0","min_plugin_version":"%s"}' "$FAKE_MIN"
    else
      printf '{"version":"0.1.0"}'
    fi
    ;;
  *raw.githubusercontent.com*)
    [ -n "${FAKE_REPO_FAIL:-}" ] && exit 1
    if [ -n "${FAKE_LATEST:-}" ]; then
      printf '{"version":"%s"}' "$FAKE_LATEST"
    else
      printf '{}'
    fi
    ;;
esac
SHIM
chmod +x "$TMP/bin/curl"

PASS=0
FAIL=0

# run_hook <installed_version> -> stdout of the hook (FAKE_* taken from env).
# TMPDIR points the hook's once-per-session marker into our scratch dir, so we
# clean only our own markers (never the global /tmp ones of a live session).
run_hook() {
  printf '{"name":"finplan","version":"%s"}' "$1" > "$TMP/root/.claude-plugin/plugin.json"
  rm -f "$TMP"/.finplan-version-check-* 2>/dev/null
  CLAUDE_PLUGIN_ROOT="$TMP/root" TMPDIR="$TMP" PATH="$TMP/bin:$PATH" bash "$HOOK"
}

ok() { PASS=$((PASS + 1)); echo "  ok - $1"; }
no() { FAIL=$((FAIL + 1)); echo "NOT ok - $1"; }

# 1. installed < min -> strong "UPDATE REQUIRED"
out=$(FAKE_MIN=2.0.0 FAKE_LATEST=2.0.0 run_hook 1.0.0)
case "$out" in *"UPDATE REQUIRED"*) ok "below min -> required" ;; *) no "below min -> required (got: $out)" ;; esac

# 2. min <= installed < latest -> gentle "UPDATE AVAILABLE" with both versions
out=$(FAKE_MIN=1.0.0 FAKE_LATEST=2.0.0 run_hook 1.5.0)
if [[ "$out" == *"UPDATE AVAILABLE"* && "$out" == *"1.5.0"* && "$out" == *"2.0.0"* ]]; then
  ok "behind latest -> available with both versions"
else
  no "behind latest -> available (got: $out)"
fi

# 3. latest present, no min (the common real-world case) -> available
out=$(FAKE_LATEST=2.0.0 run_hook 1.0.0)
case "$out" in *"UPDATE AVAILABLE"*) ok "no min, behind latest -> available" ;; *) no "no min, behind latest -> available (got: $out)" ;; esac

# 4. installed >= latest and >= min -> silent
out=$(FAKE_MIN=1.0.0 FAKE_LATEST=1.5.0 run_hook 1.5.0)
[ -z "$out" ] && ok "up to date -> silent" || no "up to date -> silent (got: $out)"

# 5. both sources unreachable -> silent, exit 0
out=$(FAKE_SERVER_FAIL=1 FAKE_REPO_FAIL=1 run_hook 1.0.0); rc=$?
if [ -z "$out" ] && [ "$rc" -eq 0 ]; then ok "both unreachable -> silent, exit 0"; else no "both unreachable -> silent (out: $out, rc: $rc)"; fi

# 6. emitted additionalContext carries real newlines (not literal backslash-n).
# Guards against double-escaping the message before json.dumps.
out=$(FAKE_LATEST=2.0.0 run_hook 1.0.0)
nl_check=$(printf '%s' "$out" | python3 -c "
import json, sys
ctx = json.load(sys.stdin)['hookSpecificOutput']['additionalContext']
print('ok' if ('\n' in ctx and '\\\\n' not in ctx) else 'bad')
" 2>/dev/null || echo "bad")
[ "$nl_check" = "ok" ] && ok "message has real newlines, not literal \\n" || no "message newline escaping (got: $out)"

echo "---"
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
