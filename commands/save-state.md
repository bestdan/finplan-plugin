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
2. Reconstruct the most recent **complete** state from the current conversation context:
   - If the most recent `manage_state` result is a **full document** (an `action="create"` result, any `manage_state` call made with `return_full_state=True`, or a **migrated** result carrying `migrated: true` — returned when the `state_json` passed in was stale, so the whole reshaped document comes back instead of a delta), use it directly.
   - If the most recent `manage_state` result is a **delta** (it has a `changed` field with `section` and `item`, and a `state_hash`, but no top-level `accounts`/`goals`/`person`), apply that delta to the full state you passed into that same `manage_state` call:
     - For list sections (`accounts`, `goals`, `income_streams`, `expenses`): replace the existing item whose id matches (`account_id` for accounts; `id` for the rest), or append it if there is no match.
     - For `person`: replace the `person` object with `changed.item`.
3. Update the `last_updated` field to today's date (YYYY-MM-DD format).
4. Strip the transient response metadata (`success`, `message`, `state_hash`, `action`, `changed`, `migrated`) before writing — a full-document result carries these merged in alongside the state fields, and they must not be persisted. Write only the state fields: `schema_fingerprint` (default to the empty string if the state being written has none — a legacy file predating the field has no fingerprint), `person`, `accounts`, `goals`, `income_streams`, `expenses`, `created_at`, `last_updated`. A migrated document already carries the current `schema_fingerprint`; persist it as-is so the file is conformant on the next load.
5. Write the full state JSON to the file using the Write tool, with consistent formatting (2-space indentation).
6. Confirm to the user that the state was saved, including the file path and a brief summary of what's in it (number of accounts, goals, etc.).

## Important

- Always preserve the complete state structure — never write a partial state. Mutation responses are deltas by default; expand them back to the full document before writing.
- If no state has been created or loaded in this session, inform the user that there is nothing to save and suggest using `/finplan:read-state` first or creating a new state via `manage_state`.
- If `$ARGUMENTS` is provided, treat it as an explicit file path to save to instead of the default location.
