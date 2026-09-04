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
    # Record the requested URL so a test can assert the fetch is channel-scoped.
    [ -n "${FAKE_URL_LOG:-}" ] && printf '%s\n' "$url" >> "$FAKE_URL_LOG"
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

# run_hook <installed_version> [installed_channel] -> stdout of the hook (FAKE_*
# taken from env). An omitted channel writes no `channel` field, which is what a
# source checkout or a --plugin-dir install looks like; the hook reads that as
# "main".
# TMPDIR points the hook's once-per-session marker into our scratch dir, so we
# clean only our own markers (never the global /tmp ones of a live session).
run_hook() {
  local channel_field=""
  [ -n "${2:-}" ] && channel_field=$(printf ',"channel":"%s"' "$2")
  printf '{"name":"finplan","version":"%s"%s}' "$1" "$channel_field" > "$TMP/root/.claude-plugin/plugin.json"
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

# --- dev-channel cases -------------------------------------------------------
# A dev sync stamps `channel` and embeds the source sha in the version string.
# Semver can't order two -dev.<sha> builds, so on a dev channel the hook compares
# the exact version string against the *same branch's* published plugin.json.

# 7. dev channel, published dev version differs -> nudge naming the channel and
#    both versions.
out=$(FAKE_LATEST=1.5.0-dev.bbbbbbb run_hook 1.5.0-dev.aaaaaaa dev)
if [[ "$out" == *"UPDATE AVAILABLE"* && "$out" == *"dev channel"* \
  && "$out" == *"1.5.0-dev.aaaaaaa"* && "$out" == *"1.5.0-dev.bbbbbbb"* ]]; then
  ok "dev channel, newer build published -> nudge naming channel and versions"
else
  no "dev channel, newer build published -> nudge (got: $out)"
fi

# 8. dev channel, same version string -> silent
out=$(FAKE_LATEST=1.5.0-dev.aaaaaaa run_hook 1.5.0-dev.aaaaaaa dev)
[ -z "$out" ] && ok "dev channel, up to date -> silent" || no "dev channel, up to date -> silent (got: $out)"

# 9. dev version string but NO channel (a source checkout / --plugin-dir install)
#    -> semver-only, and a -dev build is not < the stable base, so silent. This
#    is the regression guard: comparing a dev build against stable main is what
#    would nudge a developer who is *ahead* of main to "update" to an older
#    build.
out=$(FAKE_LATEST=1.5.0 run_hook 1.5.0-dev.aaaaaaa)
[ -z "$out" ] && ok "dev version, no channel -> silent (never nudged toward stable)" || no "dev version, no channel -> silent (got: $out)"

# 10. dev channel whose branch is gone -> the fetch 404s / returns no version ->
#     silent, like any other fetch failure.
out=$(FAKE_REPO_FAIL=1 run_hook 1.5.0-dev.aaaaaaa dev)
[ -z "$out" ] && ok "dev channel, branch gone -> silent" || no "dev channel, branch gone -> silent (got: $out)"

# 11. dev channel but below the server's hard floor -> UPDATE REQUIRED still wins.
out=$(FAKE_MIN=2.0.0 FAKE_LATEST=1.5.0-dev.bbbbbbb run_hook 1.5.0-dev.aaaaaaa dev)
case "$out" in *"UPDATE REQUIRED"*) ok "dev channel below min -> required wins" ;; *) no "dev channel below min -> required wins (got: $out)" ;; esac

# 12. the published plugin.json is fetched from the install's own channel, not
#     from main. Without this the whole dev comparison is against the wrong file.
url_log="$TMP/urls.txt"
: > "$url_log"
FAKE_URL_LOG="$url_log" FAKE_LATEST=1.5.0-dev.bbbbbbb run_hook 1.5.0-dev.aaaaaaa my-feature > /dev/null
if grep -q '/finplan-plugin/my-feature/.claude-plugin/plugin.json' "$url_log"; then
  ok "published plugin.json is fetched from the install's channel"
else
  no "channel-scoped fetch URL (got: $(cat "$url_log"))"
fi

echo "---"
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
