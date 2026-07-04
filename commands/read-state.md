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

| Argument           | What to return                                                                |
| ------------------ | ----------------------------------------------------------------------------- |
| _(empty)_          | Full state JSON                                                               |
| `person`           | Just the `person` object (including spouse and dependents)                    |
| `accounts`         | Just the `accounts` array                                                     |
| `goals`            | Just the `goals` array                                                        |
| `account <id>`     | Single account matching the given account_id                                  |
| `goal <id>`        | Single goal matching the given id                                             |
| `tax`              | Just the `tax_profile` object                                                 |
| `summary`          | A compact summary: person name/age, account names+balances, goal names+status |
| `sections <a,b,…>` | Multiple top-level sections in one object (e.g. `sections accounts,goals`)    |
| `balances-by-type` | Derived: total `balance_cents` + account count grouped by `account_type`      |
| `goals-by-status`  | Derived: goal count + summed `current_balance_cents` grouped by `status`      |
| `net-worth`        | Derived: financial-assets / real-estate / liabilities rollup + net worth      |

## Default file path

`./finplan_state.json` (override by passing a file path as the last argument)

## How to use

Based on `$ARGUMENTS`, run the appropriate `jq` command:

| Argument               | jq command                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| _(empty)_ or `summary` | `jq '{person_dob: .person.date_of_birth, income_cents: .person.annual_pretax_income_cents, marital_status: .person.marital_status, employment: .person.employment_status, zipcode: .person.zipcode, num_accounts: (.accounts \| length), account_types: [.accounts[] \| {account_id, account_type, balance_cents}], num_goals: (.goals \| length), goal_names: [.goals[] \| {id, name, goal_type}], created_at, last_updated}' FILE` |
| `person`               | `jq '.person' FILE`                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `accounts`             | `jq '.accounts' FILE`                                                                                                                                                                                                                                                                                                                                                                                                                |
| `goals`                | `jq '.goals' FILE`                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `tax`                  | `jq '.tax_profile' FILE`                                                                                                                                                                                                                                                                                                                                                                                                             |
| `account <id>`         | `jq '.accounts[] \| select(.account_id == "<id>")' FILE`                                                                                                                                                                                                                                                                                                                                                                             |
| `goal <id>`            | `jq '.goals[] \| select(.id == "<id>")' FILE`                                                                                                                                                                                                                                                                                                                                                                                        |

Where `FILE` is the state file path (default: `./finplan_state.json`).

## Multi-section fetch

Return several top-level sections in a single object instead of one call per
section. Pass the requested keys as a comma-separated list (any top-level key:
`person`, `accounts`, `goals`, `income_streams`, `expenses`, `tax_profile`, …).
Unknown keys are silently omitted rather than erroring.

```
jq --arg sections "accounts,goals" 'with_entries(select(.key as $k | ($sections | split(",") | map(gsub("^\\s+|\\s+$";""))) | index($k)))' FILE
```

Substitute the requested sections for `accounts,goals`. Example result shape:
`{"accounts": [...], "goals": [...]}`.

## Derived views (aggregations)

These compute rollups the agent would otherwise hand-roll after pulling whole
arrays. Each returns only the aggregated numbers, so the full document never
enters context. All amounts are integer cents.

| Argument           | jq command                                                                                                                                                                                |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `balances-by-type` | `jq '[.accounts[] \| {account_type, balance_cents}] \| group_by(.account_type) \| map({account_type: .[0].account_type, total_cents: (map(.balance_cents) \| add), count: length})' FILE` |
| `goals-by-status`  | `jq '[.goals[] \| {status, current_balance_cents}] \| group_by(.status) \| map({status: .[0].status, count: length, total_current_cents: (map(.current_balance_cents) \| add)})' FILE`    |
| `net-worth`        | (see the multi-line command below — it classifies each `account_type` into financial-asset / real-estate / liability and computes net worth)                                              |

The `net-worth` rollup classifies each account by `account_type`, mirroring
`finplan_core`'s asset/real-estate/liability taxonomy (liabilities are stored as
positive magnitudes and **subtracted**; net worth = financial assets + real
estate − liabilities):

```
jq '
  # Liability list mirrors finplan_core AccountCategory.LIABILITY (accounts/categories.py).
  # Keep in sync: a new liability AccountType added to core must be added here, or it
  # will fall through to "financial_asset" and inflate net worth.
  def category:
    if . == "real_estate" then "real_estate"
    elif IN("mortgage","credit_card","student_loan","auto_loan","personal_loan","other_loan") then "liability"
    else "financial_asset" end;
  [.accounts[] | {cat: (.account_type | category), balance_cents}]
  | { financial_assets_cents: (map(select(.cat=="financial_asset").balance_cents) | add // 0),
      real_estate_cents:      (map(select(.cat=="real_estate").balance_cents) | add // 0),
      liabilities_cents:      (map(select(.cat=="liability").balance_cents) | add // 0) }
  | . + {net_worth_cents: (.financial_assets_cents + .real_estate_cents - .liabilities_cents)}
' FILE
```

Where `FILE` is the state file path (default: `./finplan_state.json`).

## Important

- If the file does not exist, tell the user no state file was found and suggest creating one with `manage_state(action="create")`.
- Always use `jq` — never use `cat` or the Read tool on the state file, to avoid loading the full JSON into context.
- For the `summary` query, present the results in a readable format to the user.
