---
description: Set up API key authentication for FinPlan
allowed-tools:
  - Bash(echo *)
  - Bash(curl *)
  - Read
  - Write
  - Edit
---

# FinPlan Login

Help the user set up API key authentication for the FinPlan MCP server.

## Steps

### 1. Check for existing authentication

Read the project's `.mcp.json` using the Read tool:

```
.mcp.json
```

If the file doesn't exist, that's fine — we'll create it in step 3.

Look for `mcpServers.finplan.headers.Authorization` containing a `Bearer fp_live_...` value. **Do not print the full token** — only report whether a key is present and show the first 8 characters. If a key is already configured, skip to step 4 (verification).

### 2. Guide the user to get a key

Tell the user:

> To get an API key:
>
> 1. Create an account at **https://mcp.finplan.prethink.io/auth/signup**
> 2. After signing in, create an API key at **https://mcp.finplan.prethink.io/auth/keys**
> 3. Copy the key (it starts with `fp_live_...`) and paste it here

Wait for the user to paste their key.

### 3. Save the key

Once the user provides their key, write it to `.mcp.json` in the current working directory. This is the project-level MCP config that Claude Code reads on startup.

**Read the existing `.mcp.json`** (if it exists) using the Read tool:

```
.mcp.json
```

**Update the `mcpServers.finplan` entry** to add the auth header. Use the Edit tool if the file exists, or Write if creating from scratch. Only modify the `finplan` entry — leave all other `mcpServers` entries untouched. The result should look like:

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

Important:

- Preserve all existing settings — only add/update the `mcpServers.finplan` entry.
- If the file doesn't exist, create it with the full block above.
- If there are other mcpServers entries, keep them.
- Replace `{{BEARER_TOKEN}}` with the actual key the user provided.

After writing, confirm to the user: "Your API key has been saved to `.mcp.json` in this directory."

If the project has a `.gitignore`, check whether `.mcp.json` is already listed. If not, warn the user: "`.mcp.json` now contains your API key. Consider adding it to `.gitignore` to avoid committing it to source control."

### 4. Verify the key works

Test the key with a lightweight auth check:

```bash
curl -sf -H "Authorization: Bearer {{BEARER_TOKEN}}" https://mcp.finplan.prethink.io/auth/verify-key
```

Replace `{{BEARER_TOKEN}}` with the key the user provided.

If the response includes `"status": "authenticated"`, confirm that the API key is valid and working.

If the response is a 401 or empty, the key is invalid or revoked — help the user troubleshoot (check for typos, try regenerating at the keys page).

### 5. Restart required

Tell the user: "Restart Claude Code so the MCP server connects with your new key. Run `/exit` then start a new session from this directory."

### 6. Note on unauthenticated usage

Remind the user: FinPlan works without an API key — setting one is optional but enables authenticated features and usage tracking.
