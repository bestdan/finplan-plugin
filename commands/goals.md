---
description: View and manage your financial goals (retirement, emergency fund, education, home, major purchase)
allowed-tools:
  - Bash(jq *)
  - Skill(finplan)
  - Skill(finplan:read-state)
  - Skill(finplan:save-state)
argument-hint: [view | add | update <goal-id>]
---

# Financial Goals

View and manage the user's financial goals.

## Step 1: Load current state

Use `/finplan:read-state goals` to load goals from the local state file. Also load `/finplan:read-state person` to understand the user's age, income, and dependents for goal suggestions.

If no state file exists, inform the user and suggest running `/finplan:setup` first.

## Step 2: Display goals

Present all goals in a summary:

For each goal show:

| Field           | Display format                                                            |
| --------------- | ------------------------------------------------------------------------- |
| Name            | Goal name                                                                 |
| Type            | Formatted goal_type (e.g., `emergency_fund` → "Emergency Fund")           |
| Target          | $XXX,XXX (or "Not set" if no target_amount)                               |
| Target date     | YYYY-MM-DD or "Ongoing"                                                   |
| Current balance | $XXX,XXX                                                                  |
| Monthly contrib | $X,XXX/mo                                                                 |
| Funded by       | Linked account names (from `linked_account_ids`), or "No linked accounts" |
| Status          | active, paused, completed, etc.                                           |
| Importance      | X% success probability target                                             |

When displaying, also load `/finplan:read-state accounts` so you can resolve `linked_account_ids` to account names and show the funding relationship. If a goal's monthly contribution doesn't correspond to actual contributions flowing into linked accounts, flag the mismatch (e.g., "Goal expects $500/mo but linked 401(k) contribution is $300/mo").

If `$ARGUMENTS` is `view` or empty, stop here after displaying goals.

## Step 3a: Add a new goal

If `$ARGUMENTS` is `add`, present the common goal types and walk the user through setup:

### Suggested goal types

1. **Emergency Fund** (`emergency_fund`) — 3-6 months of expenses in liquid savings
   - Ask: monthly expenses, target months (default: 6)
   - Strategy: `minimum_balance`
   - Suggest linking to: `taxable_savings` or `taxable_checking`

2. **Retirement** (`retirement`) — Long-term retirement savings
   - Ask: target retirement age, desired annual spending in retirement
   - Strategy: `percentage_income` or `fixed_contribution`
   - Suggest linking to: `traditional_401k`, `roth_401k`, `traditional_ira`, `roth_ira`
   - Note: mention Social Security estimation is available via `estimate_social_security_pia_from_salary`

3. **Home Down Payment** (`home_downpayment`) — Save for a house purchase
   - Ask: target home price, down payment percentage (default: 20%), target purchase date
   - Strategy: `fill_to_target` or `fixed_contribution`
   - Suggest linking to: `taxable_savings` or `taxable_brokerage`

4. **Kids' Education** (`education`) — College or education fund
   - Ask: child's name and age (or birth year), target school type (public/private), years until college
   - Strategy: `fill_to_target`
   - Suggest linking to: `plan_529`
   - Target amount guidance: ~$25,000/yr public, ~$60,000/yr private (4 years)

5. **Major Purchase** (`major_purchase`) — Vehicle, renovation, wedding, etc.
   - Ask: what the purchase is, target amount, target date
   - Strategy: `fixed_contribution` or `fill_to_target`
   - Suggest linking to: `taxable_savings` or `taxable_brokerage`

### For any goal type, collect:

- **Name** — Descriptive name (e.g., "College Fund - Emma", "New Roof")
- **Target amount** — In dollars (convert to cents)
- **Target date** — YYYY-MM-DD (calculate from user input like "in 5 years" or "when I'm 65")
- **Monthly contribution** — How much they can contribute per month (or calculate via `required_monthly_cashflow`)
- **Importance** — How critical is this goal? Map to probability: essential (0.95), important (0.85), nice-to-have (0.70), aspirational (0.50)
- **Linked accounts** — Which existing accounts fund this goal. Show the user their current accounts and let them pick. The goal's contribution should align with what actually flows into those accounts — if it doesn't, note the gap and ask how they want to reconcile (adjust the goal contribution, or adjust the account contribution)

Then:

1. Call `create_goal(...)` with collected parameters
2. Call `manage_state(action="update_goal", state_json=<state>, goal_json=<result["goal"]>)`
3. Call `/finplan:save-state`
4. Optionally call `required_monthly_cashflow(...)` to show the user what monthly contribution would be needed
5. Display the new goal and any contribution guidance

## Step 3b: Update an existing goal

If `$ARGUMENTS` starts with `update`, extract the goal ID and load it with `/finplan:read-state goal <id>`.

Display the current goal details and ask what the user wants to change:

- **Target amount** — Revised target
- **Target date** — New date
- **Monthly contribution** — Adjusted amount
- **Status** — Change to active/paused/completed/abandoned
- **Importance** — Adjust priority
- **Strategy** — Change funding strategy

To update, use `create_goal(...)` with the full updated parameters (preserving the existing goal ID), then:

1. Call `manage_state(action="update_goal", state_json=<state>, goal_json=<updated_goal>)`
2. Call `/finplan:save-state`
3. Confirm the changes

## Important

- When suggesting education goals, use the number of dependents from the person profile to suggest one goal per child.
- For retirement goals, calculate the target date from current age and desired retirement age.
- When a user says "in X years", calculate the target date from today's date.
- Always run `required_monthly_cashflow` after creating a target-based goal to give the user actionable contribution guidance.
- Monetary values: always convert between dollars (user-facing) and cents (tool-facing).
