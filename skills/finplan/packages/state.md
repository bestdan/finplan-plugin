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
- **update_account** — Add or update an account in state. Requires `state_json` and `account_json`. If account has an 'id' field matching an existing account, it replaces it; otherwise adds new.
- **update_goal** — Add or update a goal in state. Requires `state_json` and `goal_json`. If goal has an 'id' field matching an existing goal, it replaces it; otherwise adds new.
- **update_person** — Update (edit) person info in state. Requires `state_json` and `person_json` with fields to change.
- **update_income_stream** — Add or update an income stream in state. Requires `state_json` and `income_stream_json`. If income stream has an 'id' field matching an existing one, it replaces it; otherwise adds new.
- **update_expense** — Add or update an expense in state. Requires `state_json` and `expense_json`. If expense has an 'id' field matching an existing one, it replaces it; otherwise adds new.

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
