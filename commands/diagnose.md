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

### 1. Check for API key

Read the project's `.mcp.json` using the Read tool:

```
.mcp.json
```

If the file doesn't exist, note this and continue — the server may work unauthenticated.

Look for `mcpServers.finplan.headers.Authorization` containing a `Bearer fp_live_...` value. If a key is found, extract the bearer token for use in the curl commands below. **Do not print the full token** — only report whether a key is present and show the first 8 characters (e.g., `fp_live_a...`).

### 2. Test server reachability

Replace `{{BEARER_TOKEN}}` with the actual token from step 1. If no key was found, omit the Authorization header entirely.

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST "https://mcp.finplan.prethink.io/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer {{BEARER_TOKEN}}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"diagnose","version":"1.0.0"}}}'
```

- `200` — server is reachable and responding
- `4xx` or `5xx` — server returned an error; note the status code
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

- **No `.mcp.json` found**: "No `.mcp.json` in this directory. Make sure you're running Claude Code from your FinPlan project directory, or run `/finplan:login` to set one up."
- **Server unreachable** (connection error or no response): "Can't reach the FinPlan server. Check your network or try again in a minute."
- **Server reachable + auth fails** (4xx or verify-key failed): "Server is up but your API key is invalid. Re-run `/finplan:login` to get a new key."
- **Server reachable + auth works + tools not in session**: "The server is fine but the MCP connection didn't establish. Restart Claude Code (`/exit` then start a new session from this directory)."
- **Server reachable + auth works + tools present**: "Everything looks good — FinPlan MCP tools are loaded and ready."

## Known setup issues

If the automated steps above don't resolve the problem, check for these common issues:

- **Plugin MCP not enabled**: After installing the plugin, the MCP server must be enabled. Go to `/plugins` → Installed → finplan and make sure MCP is toggled on. Restart the session afterward.
- **Wrong `type` in `.mcp.json`**: The MCP server type must be `"type": "url"`, not `"type": "http"`. If your `.mcp.json` has `"http"`, change it to `"url"` and restart.
- **Project `.mcp.json` overrides plugin**: If there's a `.mcp.json` in the project directory defining `mcpServers.finplan`, it completely overrides the plugin's MCP config. Make sure the project-level config is valid — check the `type` and `url` fields.
- **Key saved but not active**: `.mcp.json` is read at session startup. If you just ran `/finplan:login` and saved a key, you must restart Claude Code for the MCP server to connect with the new credentials.
- **Cached plugin version**: If you previously installed the plugin from the marketplace and are now testing with `--plugin-dir`, the cached version at `~/.claude/plugins/cache/finplan-plugin/` may take precedence. Uninstall the marketplace version first or delete the cache directory.
