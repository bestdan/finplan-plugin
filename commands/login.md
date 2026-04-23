---
description: Set up FinPlan authentication (OAuth or manual API key)
allowed-tools:
  - Bash(echo *)
  - Bash(curl *)
  - Read
  - Write
  - Edit
---

# FinPlan Login

The FinPlan MCP server requires authentication. In most cases you don't need this command — Claude Code handles sign-in automatically the first time a FinPlan tool is called. Use this command only if the automatic flow didn't run, or if you want a long-lived manual API key (e.g. for CI or scripted use).

## How to tell which path you need

### Default path — browser OAuth (no action needed)

When you invoke any FinPlan tool, the server replies with `401 + WWW-Authenticate`. Claude Code sees this, opens your browser to `https://mcp.finplan.prethink.io/auth/signup` (or login), and captures the returned token automatically. The token is stored by Claude Code internally — it is **not** written to `.mcp.json`. OAuth-issued tokens last 3 days and renew silently via the same flow on expiry.

If a FinPlan tool call opened a browser tab and you signed in, you're done. Close this command.

### When to run this command manually

- Claude Code didn't prompt for OAuth and tool calls are failing with 401.
- You want a long-lived (90-day) API key for non-interactive use — e.g. a script, Cowork, or Claude Agent SDK.
- You need to pin a specific key into `.mcp.json` for a shared project.

## Manual API key setup

### 1. Check for existing key

Read the project's `.mcp.json` using the Read tool:

```
.mcp.json
```

If the file doesn't exist, that's fine — we'll create it in step 3. If `mcpServers.finplan.headers.Authorization` already contains a `Bearer fp_live_...` value, a manual key is already configured. Report the first 8 characters only (e.g. `fp_live_a...`) — never print the full token — and skip to step 4.

### 2. Guide the user to get a key

Tell the user:

> To get a manual API key:
>
> 1. Sign in at **https://mcp.finplan.prethink.io/auth/login**
> 2. Create an API key at **https://mcp.finplan.prethink.io/auth/api-keys**
> 3. Copy the key (it starts with `fp_live_...`) and paste it here

Wait for the user to paste their key.

### 3. Save the key

Write it to `.mcp.json` in the current working directory. Use Edit if the file exists, Write if creating from scratch. Only touch the `mcpServers.finplan` entry — leave all other servers and settings untouched. Result:

```json
{
  "mcpServers": {
    "finplan": {
      "type": "url",
      "url": "https://mcp.finplan.prethink.io/mcp",
      "headers": {
        "Authorization": "Bearer {{BEARER_TOKEN}}"
      }
    }
  }
}
```

Replace `{{BEARER_TOKEN}}` with the key the user provided.

Confirm to the user: "Your API key has been saved to `.mcp.json` in this directory."

If the project has a `.gitignore`, check whether `.mcp.json` is listed. If not, warn the user: "`.mcp.json` now contains your API key. Consider adding it to `.gitignore` to avoid committing it to source control."

### 4. Verify the key

```bash
curl -sf -H "Authorization: Bearer {{BEARER_TOKEN}}" https://mcp.finplan.prethink.io/auth/verify-key
```

If the response includes `"status": "authenticated"`, the key is valid. On 401 or empty, help the user troubleshoot (typos, try regenerating at the keys page).

### 5. Restart required

Tell the user: "Restart Claude Code so the MCP server reconnects with your new key. Run `/exit` then start a new session from this directory."

## Manual key vs OAuth — which expires when

| Source                   | TTL     | Renewal                        |
| ------------------------ | ------- | ------------------------------ |
| OAuth (auto, in browser) | 3 days  | Silent re-auth via Claude Code |
| Manual key (this flow)   | 90 days | Re-run `/finplan:login`        |
