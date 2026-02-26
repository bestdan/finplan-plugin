---
description: Guided interview to set up your complete financial profile, accounts, and goals from scratch
allowed-tools:
  - Bash(jq *)
  - Skill(finplan)
  - Skill(finplan:read-state)
  - Skill(finplan:save-state)
  - Skill(finplan:profile)
  - Skill(finplan:accounts)
  - Skill(finplan:goals)
---

# Financial Setup Interview

Walk the user through a complete financial profile setup in a guided, conversational interview. This creates their profile, adds accounts, and sets up goals — everything needed for projections.

## Before starting

Check for an existing state file using `/finplan:read-state`. If one exists, show a summary and ask the user if they want to:

- **Start fresh** — Create a new state (existing file will be overwritten)
- **Update existing** — Suggest `/finplan:checkup` instead for reviewing and updating

If no state file exists, proceed with the interview.

## Interview flow

Run through each section conversationally. Ask questions naturally, confirm answers, and save state after each section. Don't dump all questions at once — go section by section.

### Section 1: Personal profile

Collect the following information:

1. **Date of birth** — "When were you born?" (need YYYY-MM-DD)
2. **Employment status** — "What's your current employment situation?" (employed, self_employed, retired, etc.)
3. **Annual pretax income** — "What's your annual income before taxes?"
4. **Marital status** — "Are you married, single, ...?"
5. **Zipcode** — "What's your zip code?" (for state tax estimates)
6. **Dependents** — "Do you have any dependents (children, etc.)?" Get count and ages if possible.

If married, also collect for spouse:

- Name, date of birth, employment status, annual pretax income

After collecting:

1. Call `manage_state(action="create", person_json={...})` with all person fields
2. Call `/finplan:save-state` immediately
3. Confirm: "Great, I've set up your profile. Here's what I have:" and display a summary

### Section 2: Accounts

Transition: "Now let's add your financial accounts. We'll go through them one at a time."

Walk through common account types by asking about each category:

1. **Retirement accounts** — "Do you have any retirement accounts? (401(k), IRA, Roth IRA, etc.)"
   - For each: type, balance, allocation, employer name, is current employer (for 401k)
   - If 401k: "Does your employer offer a match?" (note for later)
2. **Savings & checking** — "How about savings or checking accounts you'd like to track?"
3. **Investment accounts** — "Any taxable brokerage or investment accounts?"
4. **Tax-advantaged** — "Do you have an HSA or 529 education savings plan?"
5. **Real estate** — "Do you own any property?" (home value, mortgage)

For each account the user mentions:

1. Call `create_account(...)` with appropriate parameters
2. Call `manage_state(action="update_account", state_json=<state>, account_json=<result["account"]>)`
3. Call `/finplan:save-state`

After all accounts: "Here's your complete account summary:" and show the table with totals.

Ask: "Are there any other accounts I missed, or shall we move on to goals?"

### Section 3: Goals

Transition: "Now let's set up your financial goals. I'll suggest some based on your profile."

**Suggest goals based on the profile:**

- **Everyone**: Emergency fund (if no liquid savings goal), retirement
- **If has dependents**: Education fund per child
- **If no home ownership**: Home down payment (ask if interested)
- **If income allows**: Additional goals (major purchase, vacation, etc.)

Present suggestions: "Based on your profile, here are some goals to consider:"

1. **Emergency Fund** — "You should have 3-6 months of expenses set aside. What are your monthly expenses?"
2. **Retirement** — "When would you like to retire? What annual spending do you envision?"
3. **Education** (per dependent) — "For [child], do you want to save for college? Public or private?"
4. **Home Down Payment** (if relevant) — "Are you saving for a home purchase?"
5. **Other** — "Any other big financial goals? (vehicle, wedding, renovation, business, etc.)"

For each goal the user wants:

1. Collect goal-specific details (see `/finplan:goals` for per-type guidance)
2. Call `create_goal(...)` with parameters
3. Call `manage_state(action="update_goal", state_json=<state>, goal_json=<result["goal"]>)`
4. Call `/finplan:save-state`
5. Call `required_monthly_cashflow(...)` to show what's needed

After all goals: show summary of all goals with required contributions.

### Section 4: Wrap-up

After all sections are complete:

1. Display a comprehensive summary:
   - Profile overview (name/age, income, family)
   - Account totals by category
   - Goals with monthly contribution requirements
   - Total monthly savings needed across all goals
2. Compare total contributions needed vs income to flag if the plan is realistic
3. Suggest next steps:
   - "Run `/finplan:projection-dashboard` to see how your plan projects over time"
   - "Use `/finplan:checkup` periodically to review and update your plan"
   - "Ask me about specific topics like Social Security estimates, tax planning, or mortgage analysis"

## Important

- **Save after every change** — Call `/finplan:save-state` after each `manage_state` call.
- **Be conversational** — Don't present a wall of questions. Go section by section, confirming as you go.
- **Use sensible defaults** — If the user is unsure about allocation, suggest age-appropriate defaults. If unsure about emergency fund size, suggest 6 months.
- **Convert units** — User speaks in dollars, tools use cents. User says "age 65", tools need a date.
- **Don't overwhelm** — If the user seems unsure about goals, start with just emergency fund and retirement. Others can be added later.
- **Calculate ages** — Use date_of_birth and today's date to compute current age and target dates from retirement ages.
