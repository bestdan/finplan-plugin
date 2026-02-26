---
description: View and update your personal financial profile (age, income, employment, marital status, dependents)
allowed-tools:
  - Bash(jq *)
  - Skill(finplan)
  - Skill(finplan:read-state)
  - Skill(finplan:save-state)
argument-hint: [view | update]
---

# Financial Profile

View and update the user's personal financial profile.

## Step 1: Load current state

Use `/finplan:read-state person` to load the person profile from the local state file. If no state file exists, inform the user and offer to create one (jump to Step 3 with all fields).

## Step 2: Display the profile

Present the person profile in a clear, readable format:

| Field                | Display format                                    |
| -------------------- | ------------------------------------------------- |
| Date of birth        | YYYY-MM (age X)                                   |
| Employment status    | Capitalized                                       |
| Annual pretax income | Format cents as $XXX,XXX                          |
| Marital status       | Capitalized                                       |
| Zipcode              | As-is                                             |
| Dependents           | Count and ages if available                       |
| Spouse               | Name, DOB, income, employment status (if married) |

If `$ARGUMENTS` is `view` or empty, stop here after displaying the profile.

## Step 3: Offer updates

If `$ARGUMENTS` is `update`, or after displaying the profile ask the user what they'd like to update.

Updateable fields:

- **Date of birth** — Ask for YYYY-MM (month and year only). Users may not want to share the exact day. Default to the 15th when sending to tools (e.g., "1990-06" → `1990-06-15`)
- **Employment status** — `employed`, `self_employed`, `unemployed`, `retired`, `student`
- **Annual pretax income** — Dollar amount (convert to cents for the tool)
- **Marital status** — `single`, `married`, `divorced`, `widowed`
- **Zipcode** — 5-digit US zip
- **Number of dependents** — Integer count
- **Spouse info** — name, date_of_birth, employment_status, annual_pretax_income_cents (only if married)

Collect the fields the user wants to change, then:

1. Call `manage_state(action="update_person", state_json=<current_state>, person_json=<updated_fields>)`
2. Call `/finplan:save-state` immediately after
3. Confirm the changes by displaying the updated profile

## Important

- Always load state before attempting updates — never guess at current values.
- When displaying income, convert cents to dollars: divide by 100, format as `$XXX,XXX`.
- When the user provides income as dollars (e.g., "$120,000"), convert to cents (multiply by 100) before calling MCP tools.
- If the user is not married but has spouse data, note the inconsistency and ask if they'd like to update marital status.
- For dependents, if the user mentions children, confirm the number and ask for birth years if relevant to education planning.
