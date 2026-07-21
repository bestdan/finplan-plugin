# Goals Tools

Financial goal definitions, progress tracking, and contribution calculations.

## Tools

### create_goal

Create a financial goal with targets. A goal's funded amount is account-derived
(earmark an account to it via `goal_id`), so there is no manual current-balance
input — a new goal starts unfunded at $0. When the goal is added to state with
`manage_state(action="update_goal")`, a backing account is established
automatically for dedicated-savings goal types (or eligible accounts are offered
to link for retirement/education); see the state tools.

| Parameter                   | Type       | Description                                                                                                                                                                                                                                                                                |
| --------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `name`                      | string     | Goal name (1-200 chars)                                                                                                                                                                                                                                                                    |
| `goal_type`                 | string     | `"retirement"`, `"emergency_fund"`, `"education"`, `"major_purchase"`, `"home_downpayment"`, `"vacation"`, `"wedding"`, `"business_startup"`, `"vehicle_purchase"`, `"custom"`                                                                                                             |
| `importance`                | float      | Success probability target (0.01-0.99)                                                                                                                                                                                                                                                     |
| `target_amount_cents`       | int        | Target amount in cents (optional)                                                                                                                                                                                                                                                          |
| `target_date`               | string     | YYYY-MM-DD format (optional)                                                                                                                                                                                                                                                               |
| `target_date_flexibility`   | string     | `"firm"`, `"flexible"`, `"very_flexible"` (optional)                                                                                                                                                                                                                                       |
| `contribution_amount_cents` | int        | Fixed monthly contribution in cents (optional)                                                                                                                                                                                                                                             |
| `contribution_percentage`   | float      | % of income (0.0-1.0, optional)                                                                                                                                                                                                                                                            |
| `months_expenses`           | int        | Months of expenses for emergency fund (optional)                                                                                                                                                                                                                                           |
| `status`                    | string     | `"active"`, `"paused"`, `"completed"`, `"abandoned"`, `"pending"`                                                                                                                                                                                                                          |
| `tax_advantaged`            | bool       | Prefer tax-advantaged accounts (default: false)                                                                                                                                                                                                                                            |
| `notes`                     | string     | Additional notes (optional)                                                                                                                                                                                                                                                                |
| `description`               | string     | Optional longer description of the goal (max 1000 chars)                                                                                                                                                                                                                                   |
| `target_price_level`        | dict       | Price level of `target_amount_cents`. Omit for today's dollars (real purchasing power at creation). For future nominal dollars: `{"adjustment": "nominal"}`. For a specific reference purchasing power: `{"adjustment": "real", "reference_year": 2026, "reference_month": 1}` (optional). |
| `payout_schedule`           | list[dict] | Scheduled payouts for multi-year goals (e.g. education), each `{"payout_date": "YYYY-MM-DD", "amount_cents": int}` (optional).                                                                                                                                                             |
| `precondition_goal_id`      | string     | ID of a goal that must reach `precondition_threshold` before this goal is funded (optional)                                                                                                                                                                                                |
| `precondition_threshold`    | float      | Fraction (0.0-1.0) of the precondition goal that must be met first (optional)                                                                                                                                                                                                              |

### required_monthly_cashflow

Calculate the monthly contribution needed to reach a goal.

| Parameter               | Type  | Description                                                                                                   |
| ----------------------- | ----- | ------------------------------------------------------------------------------------------------------------- |
| `target_amount_cents`   | int   | Target goal amount in cents                                                                                   |
| `time_horizon_months`   | int   | Number of months until target date                                                                            |
| `initial_balance_cents` | int   | Current savings in cents (default: 0)                                                                         |
| `annual_return_rate`    | float | Expected annual return (default: 0.07)                                                                        |
| `inflation`             | float | Annual inflation rate as decimal (default: 0.0). When > 0, target is inflated to nominal value before solving |

Returns: `cashflow_cents`, `total_contributions_cents`, `projected_balance_without_new_cents`.

### get_goal_progress

Calculate current progress: percentage, remaining amount, completion status.

| Parameter    | Type | Description                                                                                           |
| ------------ | ---- | ----------------------------------------------------------------------------------------------------- |
| `goal_json`  | dict | Goal as JSON dictionary                                                                               |
| `state_json` | dict | Optional user state; derives the funded balance from accounts linked to the goal's id (default: none) |

Returns: `progress_percentage`, `remaining_amount_cents`, `is_completed`.

### project_goal_progress

Project goal progress forward with compound growth, including the goal's ongoing contributions and any scheduled payouts.

| Parameter              | Type  | Description                                                                                   |
| ---------------------- | ----- | --------------------------------------------------------------------------------------------- |
| `goal_json`            | dict  | Goal as JSON dictionary                                                                       |
| `state_json`           | dict  | Optional user state; derives the funded starting balance from linked accounts (default: none) |
| `annual_return_rate`   | float | Expected annual return (default: 0.07)                                                        |
| `annual_volatility`    | float | Return volatility; when > 0, output spreads into a p10/p25/p50/p75/p90 band (default: 0.0)    |
| `months_ahead`         | int   | Months to project forward; omit to project to the goal's own target_date (default: none)      |
| `monthly_income_cents` | int   | Monthly income in cents; only used for percentage-income goals (default: 0)                   |
| `inflation`            | float | Annual inflation rate; inflates a real-terms target (default: 0.0)                            |

### project_goal_series

Project a goal's balance and progress as a year-by-year (or N-month) series in one call — same projection as `project_goal_progress`, sampled from today through the horizon. Ideal for glide paths / drawdowns (e.g. a 529 across its tuition years) without one call per horizon.

| Parameter              | Type  | Description                                                                                                                                     |
| ---------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `goal_json`            | dict  | Goal as JSON dictionary; set current_balance_cents to the funded (linked-account) balance, or pass state_json to derive it from linked accounts |
| `state_json`           | dict  | Optional user state; derives the funded starting balance from linked accounts (default: none)                                                   |
| `annual_return_rate`   | float | Expected annual return (default: 0.07)                                                                                                          |
| `annual_volatility`    | float | Return volatility; when > 0, each point spreads into a p10/p25/p50/p75/p90 band (default: 0.0)                                                  |
| `months_ahead`         | int   | Horizon to project through; omit to run to the goal's own target_date (default: none)                                                           |
| `step_months`          | int   | Sampling cadence in months; 12 = annual, 1 = monthly (default: 12)                                                                              |
| `monthly_income_cents` | int   | Monthly income in cents; only used for percentage-income goals (default: 0)                                                                     |
| `inflation`            | float | Annual inflation rate; inflates a real-terms target (default: 0.0)                                                                              |
