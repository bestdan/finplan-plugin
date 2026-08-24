# Budget Tools

Income streams, expenses, and budget summary calculations.

## Tools

### create_income_stream

Create an income stream (salary, pension, rental, bonus, etc.).

| Parameter            | Type   | Description                                                                                                                                                               |
| -------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`               | string | Short descriptive name (e.g., "Primary Salary")                                                                                                                           |
| `income_type`        | string | `"salary"`, `"self_employment"`, `"bonus"`, `"social_security"`, `"pension"`, `"rental"`, `"investment"`, `"side_income"`, `"other"`                                      |
| `amount_cents`       | int    | Amount per occurrence in cents                                                                                                                                            |
| `frequency`          | string | `"monthly"`, `"semi_monthly"`, `"biweekly"`, `"weekly"`, `"annual"`, `"quarterly"`, `"one_time"`                                                                          |
| `is_pretax`          | bool   | Whether this is pre-tax (gross) income (default: true)                                                                                                                    |
| `start_date`         | string | YYYY-MM-DD when income begins (optional, None = already active)                                                                                                           |
| `end_date`           | string | YYYY-MM-DD when income ends (optional, None = indefinite)                                                                                                                 |
| `annual_growth_rate` | float  | Expected annual growth rate, e.g., 0.03 for 3% (default: 0.0). On a `"real"` item this is growth above inflation                                                          |
| `price_level`        | string | `"real"` (default, today's dollars, grown by inflation in `project_cashflow`) or `"nominal"` (future face value — for contractually fixed amounts like non-COLA pensions) |
| `notes`              | string | Additional notes (optional)                                                                                                                                               |

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
| `annual_growth_rate` | float  | Expected annual growth rate, e.g., 0.03 (default: 0.0). On a `"real"` item this is growth above inflation — do not set it to CPI just to keep up; `"real"` already does that                                                |
| `price_level`        | string | `"real"` (default, today's dollars, grown by inflation in `project_cashflow`) or `"nominal"` (future face value — for contractually fixed amounts like fixed-rate mortgage/loan payments)                                   |
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

**Single-date snapshot, not a forecast.** Totals are as-authored amounts filtered to items active on `as_of_date`; `annual_growth_rate` is not applied and income is not stopped at retirement beyond its own `end_date`. Every figure is today's-dollars. For a growth-applied, retirement-aware year-by-year series use `project_cashflow`.

### project_cashflow

Project income, expenses, and surplus year by year over a horizon (growth-applied, retirement-aware). Unlike `get_budget_summary` (a single today's-dollars snapshot), this returns the whole trajectory in one call — no sampling several dates by hand.

| Parameter             | Type       | Description                                                                                                                                                                  |
| --------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `horizon_years`       | int        | Number of years to project, one row per year (1–100)                                                                                                                         |
| `income_streams_json` | list[dict] | List of income stream dicts (default: [])                                                                                                                                    |
| `expenses_json`       | list[dict] | List of expense dicts (default: [])                                                                                                                                          |
| `start_date`          | string     | YYYY-MM-DD anchor date for the first year (optional, defaults to today)                                                                                                      |
| `inflation_rate`      | float      | Annual inflation (e.g. 0.03) that grows `price_level: "real"` items (the default for new items) to nominal so they hold purchasing power; nominal items ignore it (optional) |

Each year is anchored on `start_date`'s month/day advanced by whole years. Items are filtered to those active on that anchor date (a salary ending at retirement drops out, a pension starting at retirement drops in), then each active item's base annual amount is grown by `(1 + annual_growth_rate) ** year_offset` — amounts are **nominal**. A `one_time` item contributes in the single year whose window contains its date. For recurring items, year 0 matches a `get_budget_summary` snapshot at `start_date`; one-time items are the exception — `get_budget_summary` annualizes them to zero, so year 0 additionally includes any one-time amount in the first-year window.

Items tagged `price_level: "real"` (the default for newly created items) are stated in today's dollars; pass `inflation_rate` to additionally grow them by `(1 + inflation_rate) ** year_offset` so they hold purchasing power. The inflation factor multiplies on top of `annual_growth_rate`, so a real item's growth rate is growth above inflation. `"nominal"` items ignore `inflation_rate`, so omitting it reproduces the historical nominal series. Items loaded from a saved plan without an explicit `price_level` are nominal.

Returns: `start_date`, `horizon_years`, and `years` — a list of per-year rows with `year`, `as_of_date`, `total_annual_income_cents`, `total_annual_expenses_cents`, essential vs discretionary breakdown, `annual_surplus_cents`, and `savings_rate`.
