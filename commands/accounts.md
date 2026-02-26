---
description: View and manage your financial accounts (balances, allocations, add/update accounts)
allowed-tools:
  - Bash(jq *)
  - Skill(finplan)
  - Skill(finplan:read-state)
  - Skill(finplan:save-state)
argument-hint: [view | add | update <account-id>]
---

# Financial Accounts

View and manage the user's financial accounts.

## Step 1: Load current state

Use `/finplan:read-state accounts` to load accounts from the local state file. Also load the person profile with `/finplan:read-state person` to get owner IDs for new accounts.

If no state file exists, inform the user and suggest running `/finplan:setup` first to create a profile.

## Step 2: Display accounts

Present all accounts in a summary table:

| Column     | Source                                                                     |
| ---------- | -------------------------------------------------------------------------- |
| Name       | `name` or generated from account_type + institution                        |
| Type       | `account_type` formatted (e.g., `traditional_401k` → "Traditional 401(k)") |
| Balance    | `balance_cents` formatted as $XXX,XXX.XX                                   |
| Allocation | `stocks_pct / bonds_pct / cash_pct` (e.g., "60/30/10")                     |
| Tax        | `tax_treatment` formatted                                                  |

Show a total balance row at the bottom summing all account balances.

If `$ARGUMENTS` is `view` or empty, stop here after displaying accounts.

## Step 3a: Add a new account

If `$ARGUMENTS` is `add`, walk the user through creating a new account:

1. **Account type** — Present the common types grouped by category:
   - _Retirement_: `traditional_401k`, `roth_401k`, `traditional_ira`, `roth_ira`, `sep_ira`
   - _Tax-advantaged_: `hsa`, `plan_529`
   - _Taxable_: `taxable_brokerage`, `taxable_savings`, `taxable_checking`, `taxable_money_market`, `taxable_cd`
   - _Real estate_: `real_estate`, `mortgage`
   - _Other_: `ibonds`, `crypto_exchange`
2. **Balance** — Current balance in dollars (convert to cents)
3. **Allocation** — Stocks/bonds/cash percentages (must sum to 100). Suggest defaults based on account type:
   - Retirement (young): 80/15/5
   - Retirement (near retirement): 60/30/10
   - Savings/checking/CD: 0/0/100
   - HSA: 60/30/10
   - 529: 70/20/10
4. **Name** — Human-readable name (optional, suggest a default)
5. **Institution** — Financial institution (optional)
6. **Is current employer** — For 401k types only

Then:

1. Call `create_account(...)` with the collected parameters and `ownership_json={"ownership_type": "individual", "owner_ids": [<person_id>]}`
2. Call `manage_state(action="update_account", state_json=<state>, account_json=<result["account"]>)`
3. Call `/finplan:save-state`
4. Display the newly added account and updated totals

## Step 3b: Update an existing account

If `$ARGUMENTS` starts with `update`, extract the account ID and load that specific account with `/finplan:read-state account <id>`.

Display the current account details and ask what the user wants to update:

- **Balance** — New current balance
- **Allocation** — New stocks/bonds/cash split
- **Name** — Rename the account
- **Institution** — Update institution

To update, use `create_account(...)` with the full set of updated parameters, then:

1. Call `manage_state(action="update_account", state_json=<state>, account_json=<updated_account>)`
2. Call `/finplan:save-state`
3. Confirm the changes

## Important

- Always display monetary values formatted as dollars (divide cents by 100).
- When the user provides dollar amounts, convert to cents (multiply by 100) before calling tools.
- Allocation percentages must sum to exactly 100. Validate before calling tools.
- For 401k accounts, ask about employer match — note that employer match is configured separately via employer match tools, but it's a good prompt to help the user set it up.
- Group accounts by type when displaying (retirement, taxable, etc.) for readability.
