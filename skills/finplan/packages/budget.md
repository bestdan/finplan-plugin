# Budget Tools

Income streams, expenses, and budget summary calculations.

<!-- BEGIN GENERATED: tool-index budget -->

## Tool index

| Tool                   | Description                                                                                     | Parameters                                                                  |
| ---------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `create_expense`       | Create an expense (rent, utilities, insurance, etc.) with category, frequency, and growth rate. | name, category, amount_cents, frequency, is_essential?, annual_growth_rate? |
| `create_income_stream` | Create an income stream (salary, pension, rental, etc.) with type, frequency, and growth rate.  | name, income_type, amount_cents, frequency, is_pretax?, annual_growth_rate? |
| `get_budget_summary`   | Calculate a budget summary: total income, expenses, surplus/deficit, and savings rate.          | income_streams_json?, expenses_json?, as_of_date?                           |
| `project_cashflow`     | Project income, expenses, and surplus year by year (growth-applied, retirement-aware).          | horizon_years, income_streams_json?, expenses_json?, start_date?            |

<!-- END GENERATED: tool-index budget -->

## Tools

### create_income_stream

- `is_pretax` (default true) marks gross income.
- `start_date` / `end_date`: omitted start means already active, omitted end means indefinite.
- `price_level` is `"real"` (default; today's dollars, grown by inflation in `project_cashflow`) or `"nominal"` (future face value, for contractually fixed amounts like non-COLA pensions).
- On a `"real"` item, `annual_growth_rate` (decimal, e.g. 0.03; default 0.0) is growth above inflation.

### create_expense

- `is_essential` (default true) marks a non-discretionary expense.
- `start_date` / `end_date`: omitted start means already active, omitted end means indefinite.
- `price_level` is `"real"` (default; today's dollars, grown by inflation in `project_cashflow`) or `"nominal"` (future face value, for contractually fixed amounts like fixed-rate mortgage/loan payments).
- On a `"real"` item, `annual_growth_rate` (decimal, e.g. 0.03; default 0.0) is growth above inflation. Do not set it to CPI just to keep up; `"real"` already does that.

### get_budget_summary

`as_of_date` defaults to today.

**Single-date snapshot, not a forecast.** Totals are as-authored amounts filtered to items active on `as_of_date`; `annual_growth_rate` is not applied and income is not stopped at retirement beyond its own `end_date`. Every figure is today's-dollars. For a growth-applied, retirement-aware year-by-year series use `project_cashflow`.

### project_cashflow

Unlike `get_budget_summary` (a single today's-dollars snapshot), this returns the whole trajectory in one call, so there is no need to sample several dates by hand. `horizon_years` is 1-100, one row per year. `start_date` defaults to today.

Each year is anchored on `start_date`'s month/day advanced by whole years. Items are filtered to those active on that anchor date (a salary ending at retirement drops out, a pension starting at retirement drops in), then each active item's base annual amount is grown by `(1 + annual_growth_rate) ** year_offset` — amounts are **nominal**. A `one_time` item contributes in the single year whose window contains its date. For recurring items, year 0 matches a `get_budget_summary` snapshot at `start_date`; one-time items are the exception — `get_budget_summary` annualizes them to zero, so year 0 additionally includes any one-time amount in the first-year window.

Items tagged `price_level: "real"` (the default for newly created items) are stated in today's dollars and need `inflation_rate` (decimal, e.g. 0.03) to hold their purchasing power; a real item's `annual_growth_rate` is growth above inflation. `"nominal"` items ignore `inflation_rate`. Items loaded from a saved plan without an explicit `price_level` are nominal.
