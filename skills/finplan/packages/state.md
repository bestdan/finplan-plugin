# Profile & State Tools

Person profiles and user state management.

Persistence (save/load) is handled client-side via slash commands (`/finplan:read-state`, `/finplan:save-state`), not by the MCP server. These commands are bundled with the FinPlan plugin — see [SETUP.md](../SETUP.md) for installation instructions.

## Tools

### manage_state

State management tool for creating and modifying user state. Returns the full UserState JSON after every action.

| Parameter      | Type   | Description                                                                                                                                                                                           |
| -------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `action`       | string | `"create"`, `"update_account"`, `"update_goal"`, `"update_person"`                                                                                                                                    |
| `state_json`   | dict   | Current UserState JSON. Required for: update_account, update_goal, update_person.                                                                                                                     |
| `person_json`  | dict   | Person profile with fields: date_of_birth (YYYY-MM-DD), employment_status, annual_pretax_income_cents, marital_status, zipcode, optionally number_of_dependents. Required for: create, update_person. |
| `account_json` | dict   | Account from `create_account` result. Required for: update_account.                                                                                                                                   |
| `goal_json`    | dict   | Goal from `create_goal` result. Required for: update_goal.                                                                                                                                            |

**Actions:**

- **create** — Create a new UserState with person profile. Requires `person_json`.
- **update_account** — Add or update an account in state. Requires `state_json` and `account_json`. If account has an 'id' field matching an existing account, it replaces it; otherwise adds new.
- **update_goal** — Add or update a goal in state. Requires `state_json` and `goal_json`. If goal has an 'id' field matching an existing goal, it replaces it; otherwise adds new.
- **update_person** — Update (edit) person info in state. Requires `state_json` and `person_json` with fields to change.

## Typical workflow

1. `/finplan:read-state` to load existing state from local file (or skip if starting fresh)
2. `manage_state(action="create", person_json={...})` to set up profile
3. `/finplan:save-state` to persist locally
4. `create_account(...)` then `manage_state(action="update_account", ...)` then `/finplan:save-state` (repeat for each account)
5. `create_goal(...)` then `manage_state(action="update_goal", ...)` then `/finplan:save-state` (repeat for each goal)
6. `/finplan:read-state` to resume in future sessions

## State Persistence Rules

**CRITICAL**: Save the user state file after EVERY change using `/finplan:save-state`. The local state file is the source of truth.

### When to save

Call `/finplan:save-state` immediately after:

- Creating a new user state
- Adding or updating an account in the state (via `action="update_account"`)
- Adding or updating a goal in the state (via `action="update_goal"`)
- Updating person information (via `action="update_person"`)
- Any time the user provides new financial information

### How to integrate accounts and goals

Use `action="update_account"` and `action="update_goal"` to integrate created objects:

```
# Create and integrate an account
account_result = create_account(...)
state = manage_state(action="update_account", state_json=state, account_json=account_result["account"])
/finplan:save-state

# Create and integrate a goal
goal_result = create_goal(...)
state = manage_state(action="update_goal", state_json=state, goal_json=goal_result["goal"])
/finplan:save-state
```

### Common mistakes

1. **Creating accounts/goals without adding to state** - They will be lost
2. **Forgetting to save after changes** - Changes won't persist between sessions. Always call `/finplan:save-state`.
3. **Saving only at the end** - If session ends early, data is lost
