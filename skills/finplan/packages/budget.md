# Budget Tools

Income streams, expenses, and budget summary calculations.

## Tools

### create_income_stream

Create an income stream (salary, pension, rental, bonus, etc.).

| Parameter            | Type   | Description                                                                                                                          |
| -------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `name`               | string | Short descriptive name (e.g., "Primary Salary")                                                                                      |
| `income_type`        | string | `"salary"`, `"self_employment"`, `"bonus"`, `"social_security"`, `"pension"`, `"rental"`, `"investment"`, `"side_income"`, `"other"` |
| `amount_cents`       | int    | Amount per occurrence in cents                                                                                                       |
| `frequency`          | string | `"monthly"`, `"semi_monthly"`, `"biweekly"`, `"weekly"`, `"annual"`, `"quarterly"`, `"one_time"`                                     |
| `is_pretax`          | bool   | Whether this is pre-tax (gross) income (default: true)                                                                               |
| `start_date`         | string | YYYY-MM-DD when income begins (optional, None = already active)                                                                      |
| `end_date`           | string | YYYY-MM-DD when income ends (optional, None = indefinite)                                                                            |
| `annual_growth_rate` | float  | Expected annual growth rate, e.g., 0.03 for 3% (default: 0.0)                                                                        |
| `notes`              | string | Additional notes (optional)                                                                                                          |

Returns: `income_stream` dict with `monthly_amount_cents` and `annual_amount_cents`.

### create_expense

Create an expense (rent, utilities, insurance, etc.).

| Parameter            | Type   | Description                                                                                                                                                                                                                 |
| -------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`               | string | Short descriptive name (e.g., "Rent", "Car Insurance")                                                                                                                                                                      |
| `category`           | string | `"housing"`, `"utilities"`, `"transportation"`, `"food"`, `"healthcare"`, `"insurance"`, `"debt_payment"`, `"childcare"`, `"education"`, `"personal"`, `"entertainment"`, `"charitable"`, `"taxes"`, `"savings"`, `"other"` |
| `amount_cents`       | int    | Amount per occurrence in cents                                                                                                                                                                                              |
| `frequency`          | string | `"monthly"`, `"annual"`, `"quarterly"`, `"semi_annual"`, `"biweekly"`, `"weekly"`, `"one_time"`                                                                                                                             |
| `is_essential`       | bool   | Whether this is a non-discretionary expense (default: true)                                                                                                                                                                 |
| `start_date`         | string | YYYY-MM-DD when expense begins (optional, None = already active)                                                                                                                                                            |
| `end_date`           | string | YYYY-MM-DD when expense ends (optional, None = indefinite)                                                                                                                                                                  |
| `annual_growth_rate` | float  | Expected annual growth rate, e.g., 0.03 for inflation (default: 0.0)                                                                                                                                                        |
| `notes`              | string | Additional notes (optional)                                                                                                                                                                                                 |

Returns: `expense` dict with `monthly_amount_cents` and `annual_amount_cents`.

### get_budget_summary

Calculate total income, expenses, surplus/deficit, and savings rate.

| Parameter             | Type       | Description                                                     |
| --------------------- | ---------- | --------------------------------------------------------------- |
| `income_streams_json` | list[dict] | List of income stream dicts (default: [])                       |
| `expenses_json`       | list[dict] | List of expense dicts (default: [])                             |
| `as_of_date`          | string     | YYYY-MM-DD to filter active items (optional, defaults to today) |

Returns: `total_monthly_income_cents`, `total_monthly_expenses_cents`, `monthly_surplus_cents`, `savings_rate`, essential vs discretionary breakdown.
