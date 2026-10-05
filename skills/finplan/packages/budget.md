# Budget Tools

Income streams, expenses, and budget summary calculations.

<!-- BEGIN GENERATED: tool-index budget -->

## Tool index

| Tool                              | Description                                                                                                                                                                                               | Parameters                                                                                                                                                  |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `create_expense`                  | Create an expense (rent, utilities, insurance, etc.) with category, frequency, growth rate, and optional dated amount changes (amount_steps).                                                             | name, category, amount_cents, frequency, is_essential?, start_date?, end_date?, annual_growth_rate?, price_level?, amount_steps?, deductible_as?, notes?    |
| `create_income_stream`            | Create an income stream (salary, pension, rental, etc.) with type, frequency, growth rate, and optional dated amount changes (amount_steps).                                                              | name, income_type, amount_cents, frequency, is_pretax?, start_date?, end_date?, annual_growth_rate?, price_level?, amount_steps?, earner_person_id?, notes? |
| `get_budget_summary`              | Calculate a budget summary: total income, expenses, surplus/deficit, and savings rate. Takes the lines explicitly or straight from a state, and can diff two states line by line.                         | income_streams_json?, expenses_json?, as_of_date?, state_json\|state_path\|state_ref?, compare_state_json\|compare_state_path\|compare_state_ref?           |
| `project_cashflow`                | Project income, expenses, and surplus year by year (growth-applied, retirement-aware).                                                                                                                    | horizon_years, income_streams_json?, expenses_json?, start_date?, inflation_rate?                                                                           |
| `reconcile_expenses_with_actuals` | Propose expense-line changes from categorized actual spending: a catch-all run-rate, missing lines and drifted amounts, each with its evidence, plus the surplus before and after. Never edits the state. | actuals_json, state_json\|state_path\|state_ref, window?, catch_all_line?, tolerance?, one_off_threshold_cents?, as_of_date?                                |

<!-- END GENERATED: tool-index budget -->

## Tools

### create_income_stream

- `is_pretax` (default true) marks gross income. Only pre-tax streams are taxed when `project_plan` computes income tax; a false one is cash that is never taxed.
- `earner_person_id` names the person who earns the stream, for computed tax (payroll tax is per earner). Omitted, it is the stream's activation person, else the primary person.
- `start_date` / `end_date`: omitted start means already active, omitted end means indefinite.
- `price_level` is `"real"` (default; today's dollars, grown by inflation in `project_cashflow`) or `"nominal"` (future face value, for contractually fixed amounts like non-COLA pensions).
- On a `"real"` item, `annual_growth_rate` (decimal, e.g. 0.03; default 0.0) is growth above inflation.

### create_expense

- `is_essential` (default true) marks a non-discretionary expense.
- `deductible_as` (`"property_tax"`, `"charitable_cash"` or `"medical"`) marks which itemized deduction the expense feeds when `project_plan` computes income tax; omitted means not deductible. The category is unchanged, so property tax stays `housing`. A `taxes`-category expense is replaced by the computed tax — see [projection.md](projection.md#project_plan).
- `start_date` / `end_date`: omitted start means already active, omitted end means indefinite.
- `price_level` is `"real"` (default; today's dollars, grown by inflation in `project_cashflow`) or `"nominal"` (future face value, for contractually fixed amounts like fixed-rate mortgage/loan payments).
- On a `"real"` item, `annual_growth_rate` (decimal, e.g. 0.03; default 0.0) is growth above inflation. Do not set it to CPI just to keep up; `"real"` already does that.

### Dated amount changes (`amount_steps`)

Both create tools, and the items `manage_state` stores, take `amount_steps`: `[{"effective_date": "YYYY-MM-DD", "amount_cents": int}]`, sorted with no two on one date, each inside `[start_date, end_date]`. From its date a step replaces `amount_cents` (per occurrence, same frequency), and `annual_growth_rate` compounds from there. Use it for a known raise or an expense that steps down; don't split the item in two, which changes its `id`.

- **Frame.** A step is in its item's `price_level`. On a `"real"` item it is today's dollars and is inflated like the base, so enter a future face-value raise on a `"nominal"` item, or convert it to today's dollars first.
- A step dated before today is the amount in force now. A `one_time` item cannot step.
- `manage_state` replaces the whole item, so carry `amount_steps` forward when editing a saved one.

### get_budget_summary

`as_of_date` defaults to today.

**Single-date snapshot, not a forecast.** Totals are each item's amount in force on `as_of_date` (its latest `amount_steps` entry on or before it, else `amount_cents`), filtered to items active on that date; `annual_growth_rate` is not applied and income is not stopped at retirement beyond its own `end_date`. Every figure is today's-dollars. For a growth-applied, retirement-aware year-by-year series use `project_cashflow`.

**Summarize a state directly.** Pass one of `state_json`, `state_path` or `state_ref` (the same inputs `build_snapshot` takes) instead of copying the state's `income_streams` and `expenses` into `income_streams_json` / `expenses_json`. The result is identical; mixing the two is rejected.

**Before and after.** Add a second state through one of `compare_state_json`, `compare_state_path` or `compare_state_ref`. The result carries `base_summary`, `compare_summary`, and a `diff`: income and expense lines `added`, `removed` and `changed` (matched by line `id`, with `changed_fields` and the monthly amount change), each list's `unchanged_count`, and `monthly_surplus_change_cents`. Line amounts in the diff are those in force on `as_of_date`, so a step dated later changes `changed_fields` but not the amount; the surplus change counts only lines active on `as_of_date`.

### reconcile_expenses_with_actuals

Compares a state's expense lines with what the household actually spent, and returns **proposed** changes. It never writes the state; apply a proposal with `manage_state` action `update_expense`.

**The actuals shape.** `actuals_json` is a categorized spending export over a window (barclay's `transactions spend --format json`, or any source that writes the same fields):

- `window`: `{start, end}`, inclusive ISO dates. Or pass `window` as `START:END`; if both are given they must agree.
- `categories`: `{category, total_cents, transaction_count?, line?}`, one per category. `line` is the id or name of the expense line that carries the whole category.
- `recurring`: `{name, category, amount_cents, frequency, count, total_cents?, first_date?, last_date?, line?}`. `frequency` uses the expense frequencies, and `one_time` is rejected.
- `one_offs`: `{name, category, amount_cents, charge_date?}`.

Series and one-offs itemize their category's total. A series or one-off naming an unlisted category, or a category whose items sum past its total, is rejected.

**Which line carries what.** A recurring series goes to its own `line`, else to its category's `line`, else to the line with the same name (case-insensitive). If none of those applies, it is a missing line. A category with no `line` feeds `catch_all_line` when one is named, and is reported as `unassigned_monthly_cents` when none is. A series is measured at amount × frequency, so an annual fee seen once is not read as a monthly charge.

**Proposals,** each with `evidence` (the window, plus the series or category totals it was measured from):

- `catch_all`: the catch-all line's run-rate. It is its categories' totals over the window's months, less series that other lines carry and less one-offs at or above `one_off_threshold_cents` (default `50000`). Excluded one-offs are listed in `excluded_one_offs`.
- `missing_lines`: a `proposed_expense` for each series no line carries.
- `drift`: lines whose observed monthly amount is more than `tolerance` (default `0.05`) away from the recorded one. `proposed_amount_cents` is at the line's own frequency.

Lines inside tolerance are in `within_tolerance`, and lines nothing fed are in `unobserved_line_ids`. `surplus` gives the `get_budget_summary` monthly surplus before and after applying every proposal.

### project_cashflow

Unlike `get_budget_summary` (a single today's-dollars snapshot), this returns the whole trajectory in one call, so there is no need to sample several dates by hand. `horizon_years` is 1-100, one row per year. `start_date` defaults to today.

Each year is anchored on `start_date`'s month/day advanced by whole years. Items are filtered to those active on that anchor date (a salary ending at retirement drops out, a pension starting at retirement drops in), then each active item's base annual amount is grown by `(1 + annual_growth_rate) ** year_offset` — amounts are **nominal**. A `one_time` item contributes in the single year whose window contains its date. For recurring items, year 0 matches a `get_budget_summary` snapshot at `start_date`; one-time items are the exception — `get_budget_summary` annualizes them to zero, so year 0 additionally includes any one-time amount in the first-year window.

Items tagged `price_level: "real"` (the default for newly created items) are stated in today's dollars and need `inflation_rate` (decimal, e.g. 0.03) to hold their purchasing power; a real item's `annual_growth_rate` is growth above inflation. `"nominal"` items ignore `inflation_rate`. Items loaded from a saved plan without an explicit `price_level` are nominal.
