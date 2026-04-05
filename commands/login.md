---
description: Set up API key authentication for FinPlan
allowed-tools:
  - Bash(echo *)
  - Bash(curl *)
---

# FinPlan Login

Help the user set up API key authentication for the FinPlan MCP server.

## Steps

### 1. Check for existing key

Check if `FINPLAN_API_KEY` is set in the current environment:

```bash
echo "${FINPLAN_API_KEY:+set}"
```

If already set, skip to step 3 (verification).

### 2. Guide the user to get a key

Tell the user:

> To get an API key:
>
> 1. Create an account at **https://mcp.finplan.prethink.io/auth/signup**
> 2. After signing in, create an API key at **https://mcp.finplan.prethink.io/auth/keys**
> 3. Copy the key (it starts with `fp_live_...`)

Then explain how to configure it. Present **two options**:

**Option A — Environment variable (recommended)**

Add to your shell profile so it's available in all sessions:

```bash
echo 'export FINPLAN_API_KEY="your-key-here"' >> ~/.zshrc
```

Then restart your terminal or run `source ~/.zshrc`.

**Option B — Claude Code settings (per-project or global)**

Add the key directly to your Claude Code MCP settings. This avoids needing an environment variable.

In `~/.claude/settings.json` (global) or `.claude/settings.json` (project-level):

```json
{
  "mcpServers": {
    "finplan": {
      "type": "url",
      "url": "https://mcp.finplan.prethink.io/mcp",
      "headers": {
        "Authorization": "Bearer fp_live_your-key-here"
      }
    }
  }
}
```

> **How this works**: The FinPlan plugin includes an `.mcp.json` file that auto-connects to the MCP server using `${FINPLAN_API_KEY}` from your environment. If you set the env var (Option A), the plugin config picks it up automatically. Option B bypasses the env var by putting the key directly in the MCP server config.

Wait for the user to confirm they have set the key before continuing. Do NOT modify their shell profile or settings files directly.

### 3. Verify the key works

Once the user says the key is set, test it:

```bash
curl -sf -H "Authorization: Bearer ${FINPLAN_API_KEY}" https://mcp.finplan.prethink.io/auth/verify-key
```

If the response includes `"status": "authenticated"`, confirm that the API key is valid and working.

If the response is a 401 or empty (curl `-f` fails silently), the key is missing, invalid, or revoked — help the user troubleshoot.

If the user chose Option B (settings.json), the env var won't be set in the current shell. Instead, tell them: "Your key is configured in settings.json — the MCP server will pick it up on the next tool call. Let's verify by making a test call." Then try a lightweight MCP call like `search_finplan_tools(query="test")` to confirm the connection works.

### 4. Note on unauthenticated usage

Remind the user: FinPlan works without an API key — setting one is optional but enables authenticated features and usage tracking.
