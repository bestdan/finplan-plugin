---
description: Diagnose FinPlan MCP connection issues without requiring MCP tools
allowed-tools:
  - Bash(echo *)
  - Bash(curl *)
  - Read
  - ToolSearch
---

# FinPlan Diagnose

Run client-side diagnostics to identify why FinPlan MCP tools may not be loading. This command works without MCP tools being available.

## Steps

### 1. Check for a manual API key

Read the project's `.mcp.json` using the Read tool:

```
.mcp.json
```

If the file doesn't exist, continue — that's expected when Claude Code installed the plugin globally.

Look for `mcpServers.finplan.headers.Authorization` containing a `Bearer fp_live_...` value:

- **If present**: a manual key is configured. Extract the bearer token for the curl commands below. **Do not print the full token** — report only the first 8 characters (e.g. `fp_live_a...`).
- **If absent**: this is expected under the default OAuth flow. Claude Code stores OAuth-issued tokens internally, not in `.mcp.json`. Treat this as "no manual key; OAuth handles auth."

For the curl steps below, if no manual key is present, run the auth test against `/mcp` directly (which will return 401 + `WWW-Authenticate` under OAuth) rather than `/auth/verify-key`.

### 2. Test server reachability

Replace `{{BEARER_TOKEN}}` with the actual token from step 1. If no manual key was found, omit the Authorization header entirely — a 401 back is expected and actually confirms the auth layer is working.

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST "https://mcp.finplan.prethink.io/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer {{BEARER_TOKEN}}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"diagnose","version":"1.0.0"}}}'
```

- `200` — server is reachable and the bearer token authenticated
- `401` — server is reachable; bearer token missing or invalid. Under the OAuth flow this is expected when no manual key is in `.mcp.json` — Claude Code handles the 401 itself by opening the browser. A 401 from curl is **not** a problem on its own.
- Other `4xx` or `5xx` — server returned an error; note the status code
- No response or connection error — network issue or server is down

### 3. Test authentication

If a key was found in step 1, replace `{{BEARER_TOKEN}}` with the actual token:

```bash
curl -sf -H "Authorization: Bearer {{BEARER_TOKEN}}" https://mcp.finplan.prethink.io/auth/verify-key
```

If the response includes `"status": "authenticated"`, the key is valid. If the command fails silently (curl `-f` flag) or returns a 401, the key is invalid or revoked.

### 4. Check MCP tools in session

Use the `ToolSearch` tool to search for `mcp__claude_ai_FinPlan` (e.g., query `"+FinPlan_Prod ping"`). If any FinPlan tools appear in the results, the MCP connection is working. If no tools are found, the connection failed to establish during session startup.

### 5. Report results and provide guidance

Based on the results above, report what you found and give the user one of these specific next steps:

- **No `.mcp.json` + tools present in session**: "Everything looks good — Claude Code is handling FinPlan auth via OAuth automatically."
- **No `.mcp.json` + tools not in session**: "The plugin isn't configuring MCP. Check `/plugins` → Installed → finplan and ensure MCP is enabled, then restart Claude Code."
- **Server unreachable** (connection error or no response): "Can't reach the FinPlan server. Check your network or try again in a minute."
- **Manual key present + auth fails** (verify-key returned 401): "Your manual API key in `.mcp.json` is invalid or revoked. Either delete the `headers.Authorization` entry to fall back to OAuth, or re-run `/finplan:login` to get a new key."
- **Server reachable + tools not in session**: "The server is fine but the MCP connection didn't establish. Restart Claude Code (`/exit` then start a new session from this directory). If you signed in via OAuth and the token may have expired, the first tool call in the new session will re-open the browser."
- **Server reachable + tools present**: "Everything looks good — FinPlan MCP tools are loaded and ready."

## Known setup issues

If the automated steps above don't resolve the problem, check for these common issues:

- **Plugin MCP not enabled**: After installing the plugin, the MCP server must be enabled. Go to `/plugins` → Installed → finplan and make sure MCP is toggled on. Restart the session afterward.
- **Wrong `type` in `.mcp.json`**: The MCP server type must be `"type": "url"`, not `"type": "http"`. If your `.mcp.json` has `"http"`, change it to `"url"` and restart.
- **Project `.mcp.json` overrides plugin**: If there's a `.mcp.json` in the project directory defining `mcpServers.finplan`, it completely overrides the plugin's MCP config. Make sure the project-level config is valid — check the `type` and `url` fields.
- **Key saved but not active**: `.mcp.json` is read at session startup. If you just ran `/finplan:login` and saved a key, you must restart Claude Code for the MCP server to connect with the new credentials.
- **OAuth token expired mid-session**: OAuth-issued tokens last 3 days. If tool calls start failing with 401 after working earlier, Claude Code should re-open the browser on the next call. If it doesn't, restart the session to force a fresh OAuth handshake.
- **Cached plugin version**: If you previously installed the plugin from the marketplace and are now testing with `--plugin-dir`, the cached version at `~/.claude/plugins/cache/finplan-plugin/` may take precedence. Uninstall the marketplace version first or delete the cache directory.
