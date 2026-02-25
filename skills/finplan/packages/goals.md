# Goals Tools

Financial goal definitions, progress tracking, and contribution calculations.

## Tools

### create_goal

Create a financial goal with strategy and targets.

| Parameter                   | Type   | Description                                                                                                                                                                    |
| --------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `name`                      | string | Goal name (1-200 chars)                                                                                                                                                        |
| `goal_type`                 | string | `"retirement"`, `"emergency_fund"`, `"education"`, `"major_purchase"`, `"home_downpayment"`, `"vacation"`, `"wedding"`, `"business_startup"`, `"vehicle_purchase"`, `"custom"` |
| `strategy`                  | string | `"fixed_contribution"`, `"percentage_income"`, `"fill_to_target"`, `"minimum_balance"`, `"surplus_allocation"`                                                                 |
| `importance`                | float  | Success probability target (0.50-0.99)                                                                                                                                         |
| `target_amount_cents`       | int    | Target amount in cents (optional)                                                                                                                                              |
| `target_date`               | string | YYYY-MM-DD format (optional)                                                                                                                                                   |
| `target_date_flexibility`   | string | `"firm"`, `"flexible"`, `"very_flexible"` (optional)                                                                                                                           |
| `current_balance_cents`     | int    | Current savings toward goal in cents (default: 0)                                                                                                                              |
| `contribution_amount_cents` | int    | Fixed monthly contribution in cents (optional)                                                                                                                                 |
| `contribution_percentage`   | float  | % of income (0.0-1.0, optional)                                                                                                                                                |
| `months_expenses`           | int    | Months of expenses for emergency fund (optional)                                                                                                                               |
| `status`                    | string | `"active"`, `"paused"`, `"completed"`, `"abandoned"`, `"pending"`                                                                                                              |
| `tax_advantaged`            | bool   | Prefer tax-advantaged accounts (default: false)                                                                                                                                |
| `notes`                     | string | Additional notes (optional)                                                                                                                                                    |

### required_monthly_cashflow

Calculate the monthly contribution needed to reach a goal.

| Parameter               | Type  | Description                            |
| ----------------------- | ----- | -------------------------------------- |
| `target_amount_cents`   | int   | Target goal amount in cents            |
| `time_horizon_months`   | int   | Number of months until target date     |
| `initial_balance_cents` | int   | Current savings in cents (default: 0)  |
| `annual_return_rate`    | float | Expected annual return (default: 0.07) |

Returns: `cashflow_cents`, `total_contributions_cents`, `projected_balance_without_new_cents`.

### get_goal_progress

Calculate current progress: percentage, remaining amount, completion status.

| Parameter   | Type | Description             |
| ----------- | ---- | ----------------------- |
| `goal_json` | dict | Goal as JSON dictionary |

Returns: `progress_percentage`, `remaining_amount_cents`, `is_complete`.

### project_goal_progress

Project goal progress forward with compound growth (no future contributions).

| Parameter            | Type  | Description                             |
| -------------------- | ----- | --------------------------------------- |
| `goal_json`          | dict  | Goal as JSON dictionary                 |
| `annual_return_rate` | float | Expected annual return (default: 0.07)  |
| `months_ahead`       | int   | Months to project forward (default: 12) |
