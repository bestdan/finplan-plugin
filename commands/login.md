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
> 3. Copy the key and add it to your shell profile:
>
> ```bash
> echo 'export FINPLAN_API_KEY="your-key-here"' >> ~/.zshrc
> ```
>
> Then restart your terminal or run `source ~/.zshrc`.

Wait for the user to confirm they have set the key before continuing. Do NOT modify their shell profile directly.

### 3. Verify the key works

Once the user says the key is set, test it:

```bash
curl -sf -H "Authorization: Bearer ${FINPLAN_API_KEY}" https://mcp.finplan.prethink.io/auth/verify-key
```

If the response includes `"status": "authenticated"`, confirm that the API key is valid and working.

If the response is a 401 or empty (curl `-f` fails silently), the key is missing, invalid, or revoked — help the user troubleshoot.

If the key is not set or the request fails, help the user troubleshoot.

### 4. Note on unauthenticated usage

Remind the user: FinPlan works without an API key — setting one is optional but enables authenticated features and usage tracking.
