---
description: Read FinPlan user state from a local JSON file using targeted jq queries to minimize token usage
allowed-tools: Bash(jq *)
argument-hint: [section] [file-path]
---

# Read Financial Plan State

Read the user's financial plan state from the local JSON file with minimal token usage.

## State file location

Look for `*_finplan_state.json` or `finplan_state.json` in the current working directory. If multiple matches exist, use the most recently modified one.

## Arguments

`$ARGUMENTS` controls what section to read:

| Argument       | What to return                                                                |
| -------------- | ----------------------------------------------------------------------------- |
| _(empty)_      | Full state JSON                                                               |
| `person`       | Just the `person` object (including spouse and dependents)                    |
| `accounts`     | Just the `accounts` array                                                     |
| `goals`        | Just the `goals` array                                                        |
| `account <id>` | Single account matching the given account_id                                  |
| `goal <id>`    | Single goal matching the given id                                             |
| `tax`          | Just the `tax_profile` object                                                 |
| `summary`      | A compact summary: person name/age, account names+balances, goal names+status |

## Default file path

`./finplan_state.json` (override by passing a file path as the last argument)

## How to use

Based on `$ARGUMENTS`, run the appropriate `jq` command:

| Argument               | jq command                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| _(empty)_ or `summary` | `jq '{person_dob: .person.date_of_birth, income_cents: .person.annual_pretax_income_cents, marital_status: .person.marital_status, employment: .person.employment_status, zipcode: .person.zipcode, num_accounts: (.accounts \| length), account_types: [.accounts[] \| {id, account_type, balance_cents}], num_goals: (.goals \| length), goal_names: [.goals[] \| {id, name, goal_type}], created_at, last_updated}' FILE` |
| `person`               | `jq '.person' FILE`                                                                                                                                                                                                                                                                                                                                                                                                          |
| `accounts`             | `jq '.accounts' FILE`                                                                                                                                                                                                                                                                                                                                                                                                        |
| `goals`                | `jq '.goals' FILE`                                                                                                                                                                                                                                                                                                                                                                                                           |
| `tax`                  | `jq '.tax_profile' FILE`                                                                                                                                                                                                                                                                                                                                                                                                     |
| `account <id>`         | `jq '.accounts[] \| select(.id == "<id>")' FILE`                                                                                                                                                                                                                                                                                                                                                                             |
| `goal <id>`            | `jq '.goals[] \| select(.id == "<id>")' FILE`                                                                                                                                                                                                                                                                                                                                                                                |

Where `FILE` is the state file path (default: `./finplan_state.json`).

## Important

- If the file does not exist, tell the user no state file was found and suggest creating one with `manage_state(action="create")`.
- Always use `jq` — never use `cat` or the Read tool on the state file, to avoid loading the full JSON into context.
- For the `summary` query, present the results in a readable format to the user.
