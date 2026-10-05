# Goals Tools

Financial goal definitions, progress tracking, and contribution calculations.

<!-- BEGIN GENERATED: tool-index goals -->

## Tool index

| Tool                        | Description                                                                                                                                                                                                                                                                                                                                                                                          | Parameters                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `create_goal`               | Create a financial goal with specified targets.                                                                                                                                                                                                                                                                                                                                                      | name, goal_type, importance, target_amount_cents?, target_date?, target_date_flexibility?, contribution_amount_cents?, contribution_percentage?, contribution_schedule?, months_expenses?, status?, tax_advantaged?, notes?, description?, target_price_level?, payout_schedule?, deposit_schedule?, beneficiary_id?, state_json?, annual_cost_today_cents\|cost_preset?, start_age?, years?, education_inflation_premium?, start_month?, precondition_goal_id?, precondition_threshold? |
| `get_goal_progress`         | Calculate current progress toward a financial goal.                                                                                                                                                                                                                                                                                                                                                  | goal_json, state_json?                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `project_goal_progress`     | Project goal progress forward with compound growth, including the goal's ongoing contributions and scheduled payouts. With annual_volatility > 0 it returns a percentile band (p10/p25/p50/p75/p90) of balance and progress so return uncertainty is visible.                                                                                                                                        | goal_json, state_json?, annual_return_rate?, annual_volatility?, months_ahead?, monthly_income_cents?, inflation?                                                                                                                                                                                                                                                                                                                                                                        |
| `project_goal_series`       | Project a goal's balance and progress as a year-by-year (or N-month) series in one call — same projection as project_goal_progress, sampled from today through the horizon. Ideal for glide paths / drawdowns (e.g. a 529 across tuition years) without one call per horizon. Each point carries the median plus the percentile band; scheduled payouts and contributions are applied along the way. | goal_json, state_json?, annual_return_rate?, annual_volatility?, months_ahead?, step_months?, monthly_income_cents?, inflation?                                                                                                                                                                                                                                                                                                                                                          |
| `required_monthly_cashflow` | Calculate the monthly contribution needed to reach a financial goal.                                                                                                                                                                                                                                                                                                                                 | target_amount_cents, time_horizon_months, initial_balance_cents?, annual_return_rate?, inflation?                                                                                                                                                                                                                                                                                                                                                                                        |

<!-- END GENERATED: tool-index goals -->

## Tools

### create_goal

A goal's funded amount is account-derived (earmark an account to it via `goal_id`), so there is no manual current-balance input. A new goal starts unfunded at $0. When the goal is added to state with `manage_state(action="update_goal")`, a backing account is established automatically for dedicated-savings goal types (or eligible accounts are offered to link for retirement/education); see the state tools.

- `months_expenses` is required when `goal_type` is `"emergency_fund"`; otherwise unused.
- `target_price_level` sets the price level of `target_amount_cents` and of every `payout_schedule` amount. Omit it for today's dollars (real purchasing power at creation). For future nominal dollars, such as quoted future tuition bills: `{"adjustment": "nominal"}`. For a specific reference purchasing power: `{"adjustment": "real", "reference_year": 2026, "reference_month": 1}`.
- `payout_schedule` amounts are in `target_price_level`'s frame (today's dollars when omitted), so set `target_price_level` to `{"adjustment": "nominal"}` for face-value future bills.
- For tuition, prefer the generator parameters over `payout_schedule`; pass one form, never both.
- Generator parameters (`beneficiary_id`, `state_json`, `annual_cost_today_cents` or `cost_preset`, `start_age`, `years`, `education_inflation_premium`, `start_month`): `beneficiary_id` is the id of the student in `state_json`'s household (usually a dependent); their `date_of_birth` dates the school years, and it requires `state_json` and exactly one cost: `annual_cost_today_cents` or `cost_preset`. Defaults: `start_age` 18 (age in the calendar year of the first payout), `years` 4, `start_month` 8. Omit `education_inflation_premium` (e.g. `0.02`) for the 2% default, which the response flags.
- With the generator parameters, the tool builds the `payout_schedule` itself (one payout per school year, today's cost grown by the premium, in today's dollars) and sets `target_price_level` to match, so don't pass it. The response's `generated_schedule` carries the rows, the premium, whether it was the default, and any notes (cost preset, default premium, skipped past years); show them to the user.
- `cost_preset` is one of "public_in_state", "public_out_of_state" or "private_nonprofit" (four-year colleges): College Board's published cost of attendance (tuition, fees, housing and food) before aid. Use it when the user doesn't know a figure; ask "public or private?" only to pick one. It is a sticker price, so tell the user the dollar figure and year from `generated_schedule.cost_preset`, and offer to use their expected net cost as `annual_cost_today_cents` instead.

### required_monthly_cashflow

`annual_return_rate` defaults to 0.07 (decimal rate). `inflation` is a decimal rate (default 0.0); when > 0, the target is inflated to nominal value before solving.

### get_goal_progress

Pass `state_json` to derive the funded balance from accounts linked to the goal's id.

### project_goal_progress

- `state_json` derives the funded starting balance from linked accounts.
- `annual_return_rate` defaults to 0.07; `annual_volatility` > 0 spreads the output into a p10/p25/p50/p75/p90 band.
- Omit `months_ahead` to project to the goal's own `target_date`.
- `monthly_income_cents` is only used for percentage-income goals.
- `inflation` inflates a real-terms target, and a real-terms payout schedule at each payout's month. The response names each block's frame: `payout_coverage.price_level` (nominal when inflated, otherwise the goal's own `target_price_level` frame) and `remaining_payouts_price_level`.

### project_goal_series

Same projection as `project_goal_progress`, sampled from today through the horizon.

- `state_json` derives the funded starting balance from linked accounts.
- `annual_volatility` > 0 spreads each point into a p10/p25/p50/p75/p90 band.
- Omit `months_ahead` to run to the goal's own `target_date`.
- `step_months` defaults to 12 (annual); 1 = monthly.
- `monthly_income_cents` is only used for percentage-income goals.
- `inflation` inflates a real-terms target, and a real-terms payout schedule at each payout's month. `remaining_payouts_cents` stays in the goal's `target_price_level` frame, named by `remaining_payouts_price_level`.
