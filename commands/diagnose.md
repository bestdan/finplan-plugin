---
description: Diagnose FinPlan MCP connection issues without requiring MCP tools
allowed-tools:
  - Bash(echo *)
  - Bash(curl *)
---

# FinPlan Diagnose

Run client-side diagnostics to identify why FinPlan MCP tools may not be loading. This command works without MCP tools being available.

## Steps

### 1. Check environment variable

```bash
echo "${FINPLAN_API_KEY:+set}"
```

If the output is empty, `FINPLAN_API_KEY` is not set. Skip to the guidance section below — run `/finplan:login` to configure it. Do not continue with the remaining steps.

### 2. Test server reachability

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST "https://mcp.finplan.prethink.io/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer ${FINPLAN_API_KEY}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"diagnose","version":"1.0.0"}}}'
```

- `200` — server is reachable and responding
- `4xx` or `5xx` — server returned an error; note the status code
- No response or connection error — network issue or server is down

### 3. Test authentication

```bash
curl -sf -H "Authorization: Bearer ${FINPLAN_API_KEY}" https://mcp.finplan.prethink.io/auth/verify-key
```

If the response includes `"status": "authenticated"`, the key is valid. If the command fails silently (curl `-f` flag) or returns a 401, the key is invalid or revoked.

### 4. Check MCP tools in session

Use the `ToolSearch` tool to search for `mcp__claude_ai_FinPlan` (e.g., query `"+FinPlan_Prod ping"`). If any FinPlan tools appear in the results, the MCP connection is working. If no tools are found, the connection failed to establish during session startup.

### 5. Report results and provide guidance

Based on the results above, report what you found and give the user one of these specific next steps:

- **Env var not set**: "FINPLAN_API_KEY is not set. Run `/finplan:login` to set it up."
- **Server unreachable** (connection error or no response): "Can't reach the FinPlan server. Check your network or try again in a minute."
- **Server reachable + auth fails** (4xx or verify-key failed): "Server is up but your API key is invalid. Re-run `/finplan:login` to get a new key."
- **Server reachable + auth works + tools not in session**: "The server is fine but the MCP connection didn't establish. Try restarting Claude Code (`/exit` then `claude`)."
- **Server reachable + auth works + tools present**: "Everything looks good — FinPlan MCP tools are loaded and ready."
