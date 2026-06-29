# Profile & State Tools

Person profiles and user state management.

Persistence (save/load) is handled client-side via slash commands (`/finplan:read-state`, `/finplan:save-state`), not by the MCP server. These commands are bundled with the FinPlan plugin — see [SETUP.md](../SETUP.md) for installation instructions.

## Tools

### manage_state

State management tool for creating and modifying user state.

**Response shape:** `action="create"` returns the full UserState JSON (plus `success`, `message`, `state_hash`). The `update_*` actions return a **compact delta by default** — only the changed section plus a verification hash — instead of echoing the whole document back on every edit (see PRE-134):

```json
{
  "success": true,
  "message": "...",
  "action": "update_account",
  "changed": { "section": "accounts", "item": { "...": "the changed entity" } },
  "state_hash": "sha256:...",
  "last_updated": "YYYY-MM-DD"
}
```

You already hold the full state (you passed it in as `state_json`). To rebuild the document, apply `changed.item` to the section named in `changed.section`: for list sections (`accounts`, `goals`, `income_streams`, `expenses`) update-or-append by id (`account_id` for accounts; `id` for the rest); for `person` replace `.person`. `/finplan:save-state` does this for you. `state_hash` is a SHA-256 over the resulting full document so you can verify the rebuild. Pass `return_full_state=true` to get the full UserState returned inline instead.

| Parameter            | Type   | Description                                                                                                                                                                                           |
| -------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `action`             | string | `"create"`, `"update_account"`, `"update_goal"`, `"update_person"`, `"update_income_stream"`, `"update_expense"`                                                                                      |
| `state_json`         | dict   | Current UserState JSON. Required for: update_account, update_goal, update_person, update_income_stream, update_expense.                                                                               |
| `person_json`        | dict   | Person profile with fields: date_of_birth (YYYY-MM-DD), employment_status, annual_pretax_income_cents, marital_status, zipcode, optionally number_of_dependents. Required for: create, update_person. |
| `account_json`       | dict   | Account from `create_account` result. Required for: update_account.                                                                                                                                   |
| `goal_json`          | dict   | Goal from `create_goal` result. Required for: update_goal.                                                                                                                                            |
| `income_stream_json` | dict   | Income stream from `create_income_stream` result. Required for: update_income_stream.                                                                                                                 |
| `expense_json`       | dict   | Expense from `create_expense` result. Required for: update_expense.                                                                                                                                   |
| `return_full_state`  | bool   | When `true`, `update_*` actions return the full UserState inline instead of a delta (default `false`). Ignored by `create`.                                                                           |

**Actions:**

- **create** — Create a new UserState with person profile. Requires `person_json`.
- **update_account** — Add or update an account in state. Requires `state_json` and `account_json`. If account has an 'account_id' field matching an existing account, it replaces it; otherwise adds new.
- **update_goal** — Add or update a goal in state. Requires `state_json` and `goal_json`. If goal has an 'id' field matching an existing goal, it replaces it; otherwise adds new. A goal's funded amount is account-derived, so **adding a new goal establishes a backing account**: dedicated-savings types (emergency fund, vacation, …) auto-create a provisional Taxable Savings account linked to the goal (returned as `provisional_account` with `assumptions` to confirm; an auto-create returns the full document, not a delta); retirement/education and ambiguous types instead return `eligible_accounts` to link plus a `warnings` entry that the goal is not yet funded. A multi-owner household defers the auto-create with a `warnings` entry + `candidate_owner_ids`. Editing an existing goal never re-runs establishment.
- **update_person** — Update (edit) person info in state. Requires `state_json` and `person_json` with fields to change.
- **update_income_stream** — Add or update an income stream in state. Requires `state_json` and `income_stream_json`. If income stream has an 'id' field matching an existing one, it replaces it; otherwise adds new.
- **update_expense** — Add or update an expense in state. Requires `state_json` and `expense_json`. If expense has an 'id' field matching an existing one, it replaces it; otherwise adds new.

### describe_state_schema

Return the JSON Schema for a `finplan_state` document. Fetch it **once** to author a valid state in a single pass, instead of discovering required fields by submitting and reading validation errors. The schema describes every nested shape under `json_schema["$defs"]` — including the `PeriodRate` / `ReturnPeriod` rate types and all enums such as `property_type` — so you don't have to probe level-by-level.

Takes no parameters. Returns `{kind, schema_fingerprint, json_schema}`. The result is static for a given server version and safe to cache; `schema_fingerprint` identifies the schema version a document must match.

### migrate_state

Upgrade a state document to the current schema **once** and hand it back as a download. An unstamped or stale document makes every `build_snapshot` re-migrate it; this runs the shared ingest path (validate → migrate → stamp `kind` + `schema_fingerprint`), writes the upgraded document to file storage, and returns a download URL plus a compact summary — never the full document inline. Persist the downloaded document (e.g. via `/finplan:save-state`); subsequent `build_snapshot` calls then see a conformant document and report `migrated: false`, ending the re-migration loop.

| Parameter    | Type | Description                                                                                                          |
| ------------ | ---- | -------------------------------------------------------------------------------------------------------------------- |
| `state_json` | dict | A `finplan_state` document to upgrade. May be unstamped or stale; it is validated and re-stamped on the way through. |

Returns `{success, urls, summary}` on success — the migrated document lives at `urls.data`, and `summary` carries `kind`, `schema_hash`, `migrated`, `schema_drift`, and `warnings`. Returns an error envelope with structured `errors` when the document cannot validate.

### link_account

Persist external-sync crosswalk links onto FinPlan accounts so a Monarch↔FinPlan link is confirmed **once** and every later sync matches deterministically on `external_id`. Batch and many-to-one (several source ids onto one FinPlan account); appending an already-linked id is a no-op. The whole batch fails (nothing persisted) if any `finplan_account_id` is unknown, if an id is already linked to a different account, or if the account is already linked to a different `system`. Returns the linked-account summaries and a new `state_ref`.

| Parameter    | Type   | Description                                                                                                                   |
| ------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `links`      | list   | Links to persist, each `{finplan_account_id, external_ids}` (external_ids is a list of source ids mapping onto that account). |
| `state_json` | dict   | Inline planning-state document (provide exactly one of state_json, state_path, state_ref).                                    |
| `state_path` | string | Path to a state file on disk, stdio only (one-of).                                                                            |
| `state_ref`  | string | Handle to an already-uploaded state document (one-of).                                                                        |
| `system`     | string | The external source system being linked (default: monarch).                                                                   |

### unlink_account

Remove some or all external-sync crosswalk links from a FinPlan account. With `external_ids`, only those ids are removed; omitting them clears the account's link entirely. Scoped to one `system`; a no-op (wrong system, or ids not present) succeeds without churning state. Returns the remaining link state, a `changed` flag, and a `state_ref`.

| Parameter            | Type   | Description                                                                                |
| -------------------- | ------ | ------------------------------------------------------------------------------------------ |
| `finplan_account_id` | string | The FinPlan account to unlink.                                                             |
| `state_json`         | dict   | Inline planning-state document (provide exactly one of state_json, state_path, state_ref). |
| `state_path`         | string | Path to a state file on disk, stdio only (one-of).                                         |
| `state_ref`          | string | Handle to an already-uploaded state document (one-of).                                     |
| `external_ids`       | list   | Source ids to remove; omit to clear the account's crosswalk entirely (default: none).      |
| `system`             | string | The external source system to unlink (default: monarch).                                   |

## Typical workflow

1. `/finplan:read-state` to load existing state from local file (or skip if starting fresh)
2. `manage_state(action="create", person_json={...})` to set up profile
3. `/finplan:save-state` to persist locally
4. `create_account(...)` then `manage_state(action="update_account", ...)` then `/finplan:save-state` (repeat for each account)
5. `create_goal(...)` then `manage_state(action="update_goal", ...)` then `/finplan:save-state` (repeat for each goal)
6. `create_income_stream(...)` then `manage_state(action="update_income_stream", ...)` then `/finplan:save-state` (repeat for each income source)
7. `create_expense(...)` then `manage_state(action="update_expense", ...)` then `/finplan:save-state` (repeat for each expense)
8. `/finplan:read-state` to resume in future sessions

## State Persistence Rules

**CRITICAL**: Save the user state file after EVERY change using `/finplan:save-state`. The local state file is the source of truth.

### When to save

Call `/finplan:save-state` immediately after:

- Creating a new user state
- Adding or updating an account in the state (via `action="update_account"`)
- Adding or updating a goal in the state (via `action="update_goal"`)
- Adding or updating an income stream in the state (via `action="update_income_stream"`)
- Adding or updating an expense in the state (via `action="update_expense"`)
- Updating person information (via `action="update_person"`)
- Any time the user provides new financial information

### How to integrate accounts and goals

Use the `update_*` actions to integrate created objects:

Each `update_*` returns a delta; apply it to the state you passed in (or let `/finplan:save-state` do it) to keep your full document current.

```
# Create and integrate an account
account_result = create_account(...)
delta = manage_state(action="update_account", state_json=state, account_json=account_result["account"])
state = apply_delta(state, delta)   # update-or-append changed.item into changed.section
/finplan:save-state

# Create and integrate a goal
goal_result = create_goal(...)
delta = manage_state(action="update_goal", state_json=state, goal_json=goal_result["goal"])
state = apply_delta(state, delta)
/finplan:save-state

# Create and integrate an income stream
income_result = create_income_stream(...)
delta = manage_state(action="update_income_stream", state_json=state, income_stream_json=income_result["income_stream"])
state = apply_delta(state, delta)
/finplan:save-state

# Create and integrate an expense
expense_result = create_expense(...)
delta = manage_state(action="update_expense", state_json=state, expense_json=expense_result["expense"])
state = apply_delta(state, delta)
/finplan:save-state
```

### Common mistakes

1. **Creating accounts/goals/income/expenses without adding to state** - They will be lost
2. **Forgetting to save after changes** - Changes won't persist between sessions. Always call `/finplan:save-state`.
3. **Saving only at the end** - If session ends early, data is lost
