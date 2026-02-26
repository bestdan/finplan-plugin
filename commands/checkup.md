---
description: Review your financial plan for life changes, update profile/accounts/goals, and identify gaps
allowed-tools:
  - Bash(jq *)
  - Skill(finplan)
  - Skill(finplan:read-state)
  - Skill(finplan:save-state)
  - Skill(finplan:profile)
  - Skill(finplan:accounts)
  - Skill(finplan:goals)
---

# Financial Checkup

Review the user's existing financial plan, flag anything that may need updating based on life changes, and walk through updates conversationally.

## Step 1: Load current state

Use `/finplan:read-state` to load the full state summary. If no state file exists, inform the user and suggest running `/finplan:setup` first.

## Step 2: Display current snapshot

Show a concise overview of the current plan:

- **Profile**: Name, age, income, marital status, dependents, employment
- **Accounts**: Count, total balance, breakdown by category (retirement, taxable, tax-advantaged)
- **Goals**: Count, summary of each (name, type, status, progress toward target)

Then: "Let's review your plan and see if anything needs updating."

## Step 3: Profile review

Ask about life changes that affect financial planning:

- "Has your income changed?" — If yes, update via `manage_state(action="update_person")`
- "Any change in employment?" — New job, self-employed, retired
- "Has your marital status changed?" — Marriage, divorce, widowhood
- "Any new dependents?" — New child, elderly parent
- "Have you moved?" — New zipcode for tax estimates

For any changes:

1. Call `manage_state(action="update_person", state_json=<state>, person_json=<changes>)`
2. Call `/finplan:save-state`

## Step 4: Account review

Walk through existing accounts and check for updates:

- "Have any account balances changed significantly?" — Update balances
- "Any new accounts to add?" — Walk through account creation (see `/finplan:accounts add`)
- "Any accounts to close or remove?" — Mark as inactive
- "Has your investment allocation changed?" — Update allocation percentages
- "Any changes to employer 401(k) match?" — Note for employer match tools

For each update:

1. Use `create_account(...)` with updated values, then `manage_state(action="update_account")`
2. Call `/finplan:save-state` after each change

## Step 5: Goal review

Review each existing goal:

For each active goal:

- "Is [goal name] still a priority?" — If not, offer to pause or abandon
- "Has the target amount or date changed?" — Update if needed
- Call `get_goal_progress(goal_json=<goal>)` to show current progress
- Flag if the goal is falling behind (progress % vs time elapsed %)

Then check for **new goals based on life changes**:

| Life change         | Suggested new goal                                                                  |
| ------------------- | ----------------------------------------------------------------------------------- |
| New child/dependent | Education fund (529) — "Would you like to start a college fund for your new child?" |
| Marriage            | Update retirement to joint planning, consider home purchase if renting              |
| Income increase     | Increase retirement contributions, consider new investment goals                    |
| Home purchase       | Mortgage tracking, home maintenance fund                                            |
| Approaching 50+     | Catch-up contributions, Social Security planning                                    |
| New job             | Review 401k options, rollover old 401k                                              |
| Self-employed       | SEP IRA, business emergency fund                                                    |

For new goals:

1. Collect details (see `/finplan:goals add` for per-type guidance)
2. Call `create_goal(...)`, then `manage_state(action="update_goal")`
3. Call `/finplan:save-state`
4. Call `required_monthly_cashflow(...)` for contribution guidance

## Step 6: Summary and recommendations

After the review, present:

1. **Changes made** — List all updates applied during this checkup
2. **Updated snapshot** — Current profile, account totals, goal progress
3. **Monthly cashflow check** — Total contributions needed across all goals vs income
   - Flag if total contributions exceed a reasonable percentage of income (e.g., >50% of take-home)
4. **Recommendations**:
   - Goals that need increased contributions
   - Accounts that might benefit from rebalancing
   - Missing goals (e.g., no emergency fund, no retirement savings)
   - Upcoming milestones (approaching retirement, kids starting college, RMD age)
5. **Next steps**:
   - "Run `/finplan:projection-dashboard` to see updated projections"
   - "Ask about specific topics: Social Security, tax optimization, mortgage analysis"

## Important

- **Save after every change** — Call `/finplan:save-state` after each `manage_state` call.
- **Be conversational** — Don't ask all questions at once. Go section by section.
- **Be proactive with suggestions** — The value of a checkup is catching things the user hasn't thought about. Use the life-change-to-goal mapping above.
- **Show progress** — For each goal, show how much progress has been made and whether they're on track.
- **Don't force changes** — If the user says everything is the same, confirm that their plan looks good and skip to recommendations.
- **Calculate ages and dates** — Use date_of_birth to compute age-based milestones and flag upcoming ones.
