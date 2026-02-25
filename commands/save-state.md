---
description: Save the current FinPlan user state JSON to the local file system after any state modification
allowed-tools:
  - Write
  - Glob
argument-hint: [file-path]
---

# Save Financial Plan State

Write the current user state JSON to the local file system.

## State file location

Save to the same `*_finplan_state.json` file in the current working directory that was most recently read or created. If no state file exists yet, save to `finplan_state.json` in the working directory.

## How to save

1. Find the existing state file using Glob for `*finplan_state.json` in the working directory.
2. Identify the most recent version of the state from the current conversation context. This is typically the result returned by the most recent `manage_state` MCP tool call.
3. Update the `last_updated` field to today's date (YYYY-MM-DD format).
4. Write the full state JSON to the file using the Write tool, with consistent formatting (2-space indentation).
5. Confirm to the user that the state was saved, including the file path and a brief summary of what's in it (number of accounts, goals, etc.).

## Important

- Always preserve the complete state structure — never write a partial state.
- If no state has been created or loaded in this session, inform the user that there is nothing to save and suggest using `/finplan:read-state` first or creating a new state via `manage_state`.
- If `$ARGUMENTS` is provided, treat it as an explicit file path to save to instead of the default location.
