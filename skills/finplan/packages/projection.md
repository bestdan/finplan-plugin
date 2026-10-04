# Projection Tools

Project investment growth with uncertainty using analytical or Monte Carlo methods.

**Terminology:**

- **Constant-return mode**: Input mode where you provide fixed `expected_annual_return` and `annual_volatility`
- **Timeline mode**: Input mode where you provide time-varying returns via `return_distribution_timeline` (glide paths)
- **Projection methods**: Computation approaches (`closed_form` = analytical, `monte_carlo` = simulation, `deterministic` = no uncertainty, `auto` = automatically select)

<!-- BEGIN GENERATED: tool-index projection -->

## Tool index

| Tool                         | Description                                                                                                                                                                   | Parameters                                                                                                                  |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `compare_return_assumptions` | Compare market outcomes under conservative, moderate, and aggressive return assumptions (not plan scenarios).                                                                 | initial_balance_cents, years?, num_simulations?                                                                             |
| `project_plan`               | Project a whole household plan from UserState: per-account projections aggregated into one after-tax outcome, with each year's income tax computed and taken off the surplus. | state_json, time_horizon_months?, assumptions_preset?, inflation?, compute_income_tax?, marginal_ordinary_rate?, ltcg_rate? |
| `run_projection`             | Run a financial projection (closed-form or Monte Carlo) with constant or time-varying returns.                                                                                | initial_balance_cents, expected_annual_return?, annual_volatility?, time_horizon_months?                                    |
| `run_projections`            | Batch run_projection: run many independent projections in parallel in one call (per-account or per-allocation fan-out).                                                       | projections[{initial_balance_cents, expected_annual_return?, ...}]                                                          |

<!-- END GENERATED: tool-index projection -->

## Tool notes

### run_projection

**Two input modes. Provide either, not both:**

1. **Constant returns** — `expected_annual_return` (0.07 = 7%), `annual_volatility` (0.15 = 15%), and `time_horizon_months` (required in this mode). Supports `fees`, `inflation`, and custom `percentiles`.
2. **Time-varying returns** — `return_distribution_timeline` with monthly entries for glide paths: `{"month": 1, "return": 0.07, "volatility": 0.15}` (1-indexed, sequential). The time horizon is derived from the timeline length.

`inflation` (default 0.025; 0 gives nominal dollars) and `percentiles` (default [10, 25, 50, 75, 90]) apply to constant-return mode only.

**Contribution inputs:**

- `monthly_contribution_cents` is a constant monthly contribution (default 0); negative means withdrawal. In retirement mode it is the pre-retirement (accumulation) contribution. It is mutually exclusive with `contribution_timeline`.
- `contribution_timeline` is `{month, contribution_cents}` per month (1-indexed, sequential, one entry per month of the horizon; negative means withdrawal). It is mutually exclusive with `monthly_contribution_cents` and `retirement_month`.
- `retirement_month` is the 1-indexed month at which contributions flip to withdrawals, in a single call. It is mutually exclusive with `contribution_timeline`.
- `retirement_withdrawal_cents` (gross monthly, >= 0) and `retirement_income_cents` (monthly income such as Social Security offsetting the withdrawal, >= 0) both default to 0 and both require `retirement_month`.

**Other inputs:**

- `method` is `"closed_form"` (default), `"auto"`, `"deterministic"`, or `"monte_carlo"`. `iterations` defaults to 1000; `seed` pins the Monte Carlo draw, and omitting it uses a fixed default.
- `cumulative_volatility` applies to `method="closed_form"` only (ignored otherwise). True (default) compounds volatility cumulatively (scales with sqrt(T)), widening percentile spreads as the horizon grows. False uses average per-period volatility (roughly constant spreads) and keeps a projection with cashflows on the analytic form, which is less accurate in the tails.
- `fees` is stackable, e.g. `[{"type": "flat_percent", "annual_rate": 0.005}]` (percent of AUM) or `[{"type": "flat_dollar", "annual_amount_cents": 500000}]` (fixed dollars/year). A `flat_dollar` fee also takes `price_level`: `"nominal"` (default) is an unindexed contract amount, so its real cost falls as prices rise; `"real"` is a today's-dollars amount that tracks inflation and holds its purchasing power. Two `flat_dollar` fees in different price levels are rejected — they sum into one rail, which carries one frame.
- `summary_only=true` skips the per-month time-series data file and returns only the inline summary (`final_balance_percentiles` plus scalar metadata). Use it for headline-only reads such as per-account breakdown tables, to avoid a file artifact per call. Default false keeps the full timeline.

The response is described under [Working with file-based responses](#working-with-file-based-responses). All monetary values are in **cents**.

### run_projections

Use this instead of N serial `run_projection` calls whenever you have several same-shape, independent projections (a per-account retirement breakdown, one chart series per allocation, etc.). Each `projections` entry is a `run_projection` parameter object: at minimum `{initial_balance_cents}` plus either constant-return params or a `return_distribution_timeline`.

Up to 50 projections per call. `projections` in the response holds one result per input entry, **in the same order**. A malformed entry yields a per-entry `{success: false, error, message}` in its slot without failing the others.

### compare_return_assumptions

Compares conservative (5%/8%), moderate (7%/15%), and aggressive (9%/22%) return assumptions. `years` defaults to 30 and `num_simulations` to 1000 per assumption set. `inflation` defaults to 0.025; when > 0, results are in today's purchasing power, and 0 gives nominal dollars.

### project_plan

Supply either the full `state_json` or a live `state_ref`; inline state takes precedence. The response returns `summary.inputs.base_state_ref`, reusable as `state_ref` while live. Refs have an approximately 60-minute sliding TTL that refreshes on each use; on `state_ref_expired`, re-send the full `state_json` in that same call.

- Liability and real-estate accounts are reported under `skipped_accounts`, not projected.
- Each account's after-tax figure is a full-liquidation haircut: its projected balance scaled by that account's withdrawal tax treatment, as if the whole balance were cashed out in that month. It is not a tax on withdrawals as they happen.
- Defaults: `time_horizon_months` 360; `assumptions_preset` `"standard"` (or `"conservative"`, `"optimistic"`); `inflation` 0.025 (when > 0, values are in today's purchasing power; 0 gives nominal dollars); `marginal_ordinary_rate` 0.22 and `ltcg_rate` 0.15 for after-tax values; `iterations` 1000 and `seed` apply only to `method="monte_carlo"`; `seed` pins the draw, and omitting it uses a fixed default.
- `invest_residual_surplus` (default true) invests the household surplus left over after account contribution pins across the remaining accounts by balance. Set false to hold the leftover out of the plan.
- Accounts are projected independently and aggregated by summing matching percentiles (a perfectly-correlated / comonotonic assumption), surfaced in the response `assumptions` block.
- An account contribution pin (a current-employer 401(k)'s employee deferral) is honored first. A configured `employer_match` on that plan is computed on the employee contribution and the household's annual W-2 compensation and routed on top (reported per account as `monthly_employer_match_cents`), so employer money compounds instead of being folded into one undifferentiated surplus.

**Income tax is computed by default.** For each calendar year, federal (with NIIT and Additional Medicare), state, local, and employee FICA plus self-employment tax are computed from the income streams, pre-tax 401(k) deferrals, mortgages and `deductible_as` expenses, and subtracted from the surplus before it is invested. The surplus is therefore after tax, which lowers projected balances for any plan with taxable income.

- **Inputs come from the state**, set with `manage_state`: the person's `filing_status`, `residence_state` and `residence_locality` (`update_person`), an income stream's `earner_person_id`, and an expense's `deductible_as`. `create_income_stream` and `create_expense` also take the last two. Unset, filing status derives from `marital_status` and dependents, and the state from the ZIP; the locality is never derived. The notes name each assumption.
- **It replaces hand-entered `TAXES` expenses**, except one marked `deductible_as: "property_tax"`, and the notes name each one replaced. Pass `compute_income_tax: false` to keep your own figure and invest the pre-tax surplus.
- **No tax when no profile resolves.** With an unreadable person, or `filing_status: "married_filing_separately"` on a married person whose spouse is recorded (one return per household cannot hold two separate returns), the plan is projected without computed tax, `TAXES` expenses are kept, and the first note says why.
- **Output.** The data file's `income_tax_by_year` has one row per calendar year the horizon touches: `federal_cents`, `state_cents`, `local_cents` (`null` when not computed), `fica_cents`, `total_cents`, `is_projected` (parameters projected past enacted law), `federal_rates` and `notes`. Each row is the whole calendar year in the result's price level; a partial first or last year was charged only its projected months' share. `federal_rates` (marginal and effective) are scale-free. `summary.outputs.first_year_income_tax` repeats the first row, and `income_tax_computed` says whether tax was computed.
- **`monthly_surplus_cents`** is the as-of surplus. With computed tax it is after tax: the as-of surplus less the first projected month's tax, a twelfth of that year's.
- `compare_scenarios` computes the tax the same way for the base and every scenario, so a delta includes its tax consequence; it takes the same `compute_income_tax` flag.
- The after-tax balance haircut (`marginal_ordinary_rate`, `ltcg_rate`) is separate and unchanged: it taxes balances as if liquidated, not income.

**Limits.** Three decumulation behaviors `project_plan` does not model.

- **Deficit drawdowns are untaxed.** When household spending (plus computed income tax) exceeds income, the monthly deficit is funded as a negative contribution — a proportional drawdown from the accounts that carry no `monthly_contribution_cents` pin — with no tax taken at the point of withdrawal. The plan funds that spending with gross dollars, so it overstates what the accounts can support. When every projected account is pinned there is no unpinned account to draw from, and the deficit is not funded at all.
- **Age rules never fire.** This path resolves the budget without a household person list, so every `start_age`/`end_age` rule is unresolvable: an age-gated income stream (Social Security, a pension) is dropped for the whole horizon and an age-bounded expense runs for all of it. Income is understated and spending overstated wherever an age rule is set. No tool evaluates these rules today — `get_budget_summary` filters on `start_date`/`end_date` only — so there is no second tool to call for the age-aware answer.
- **RMDs are not forced.** Nothing in the projection distributes a pre-tax balance at the required beginning date, taxes it, or reinvests what is left, so a pre-tax account compounds past the age the IRS would have forced money out of it. The RMD tools are calculators the projection never calls — see [rmd.md](rmd.md).

The first two limits also appear in the response's `assumptions` block when a plan triggers them; the RMD limit does not.

## Working with file-based responses

Unless you pass `summary_only=true`, the response includes URLs + compact inline summary: `summary` (final balance percentiles, inputs, method info), `urls.schema` (data dictionary), `urls.data` (full time series), and `projection_ref` (a handle to pass to [after-tax projections](#after-tax-projections)). With `summary_only=true` only `summary` comes back. Use `summary` for statistics and `jq` for targeted queries. Don't load data files into context — see [SKILL.md](../SKILL.md#data-files-stay-out-of-context).

The data file schema is:

```json
{
  "net_deposits": [{ "month": 0, "net_deposits_cents": 50000000 }, "..."],
  "percentile_timelines": {
    "p10": [
      { "month": 0, "total_value_cents": 50000000, "cumulative_investment_return_cents": 0 },
      "..."
    ],
    "p25": ["...same shape..."],
    "p50": ["...same shape..."],
    "p75": ["...same shape..."],
    "p90": ["...same shape..."]
  },
  "inputs": { "initial_balance_cents": 50000000, "...": "..." },
  "outputs": { "final_balance_percentiles": { "p10": { "cents": 0, "dollars": 0 }, "...": "..." } },
  "projection_result": { "scenario_id": "...", "iterations": 10000, "time_horizon_months": 360 }
}
```

```bash
# Download urls.data once, then query the local copy with jq
mkdir -p "${TMPDIR:-/tmp}/finplan"
curl -s "<urls.data>" -o "${TMPDIR:-/tmp}/finplan/projection_data.json"
jq '.percentile_timelines.p50[-1].total_value_cents' "${TMPDIR:-/tmp}/finplan/projection_data.json"
jq '{p10: .percentile_timelines.p10[-1].total_value_cents, p90: .percentile_timelines.p90[-1].total_value_cents}' "${TMPDIR:-/tmp}/finplan/projection_data.json"
jq '.net_deposits[12].net_deposits_cents' "${TMPDIR:-/tmp}/finplan/projection_data.json"
```

For embedding data in HTML dashboards, use bash to inject file contents directly — see [file-tools.md](file-tools.md).

## Withdrawals (Retirement Phase)

**Negative contributions work as withdrawals.** To model a pure spending phase (drawing down from day one), use a negative `monthly_contribution_cents`. To model saving _then_ spending in one call, use `retirement_month` (see below).

A 30-year retirement drawing $4,000/month from $500k — `run_projection` with these arguments:

```json
{
  "initial_balance_cents": 50000000,
  "monthly_contribution_cents": -400000,
  "expected_annual_return": 0.05,
  "annual_volatility": 0.10,
  "time_horizon_months": 360
}
```

### Multi-phase planning (accumulation -> retirement)

Use `retirement_month` to model saving up to retirement and drawing down after it in a **single call**. Months before it contribute `monthly_contribution_cents`; from it onward the monthly cashflow is `retirement_income_cents - retirement_withdrawal_cents`.

Saving $2k/month for 20 years from $100k, then withdrawing $5k/month offset by $2k/month of Social Security for 30 years — `run_projection` with these arguments (month 241 is the first month of retirement; 600 months = 20 accumulating + 30 in retirement):

```json
{
  "initial_balance_cents": 10000000,
  "monthly_contribution_cents": 200000,
  "retirement_month": 241,
  "retirement_withdrawal_cents": 500000,
  "retirement_income_cents": 200000,
  "expected_annual_return": 0.06,
  "annual_volatility": 0.12,
  "time_horizon_months": 600
}
```

Don't chain two calls (feeding one projection's p50 into the next as the starting balance): it understates uncertainty by collapsing the first phase to a single percentile.

### Time-varying contributions

When saving or spending changes month to month (a raise, a sabbatical, a lumpy expense), pass `contribution_timeline` instead of a scalar — one entry per month of the horizon, written out in full.

Saving $2k/month for three months, then $3k/month after a raise — `run_projection` with these arguments:

```json
{
  "initial_balance_cents": 10000000,
  "contribution_timeline": [
    { "month": 1, "contribution_cents": 200000 },
    { "month": 2, "contribution_cents": 200000 },
    { "month": 3, "contribution_cents": 200000 },
    { "month": 4, "contribution_cents": 300000 },
    { "month": 5, "contribution_cents": 300000 },
    { "month": 6, "contribution_cents": 300000 }
  ],
  "expected_annual_return": 0.07,
  "annual_volatility": 0.15,
  "time_horizon_months": 6
}
```

## After-tax projections

To compute after-tax spendable values from a projection, use `apply_after_tax_to_projection_result` (in the [Tax tools](tax.md)):

1. Run `run_projection` (without `summary_only`) to get pre-tax results. Its response carries a `projection_ref`, a handle to the full projection in the server's file store.
2. Pass that `projection_ref` to `apply_after_tax_to_projection_result` with the account's tax treatment and the user's tax rates. The server loads the time series itself, so nothing is fetched into context.

Don't pass `summary.projection_result` from the inline response: its percentiles are stripped, and the tool rejects it.

For a Traditional 401(k) at a 22% marginal rate, `apply_after_tax_to_projection_result` takes these arguments, with `projection_ref` copied from step 1:

```json
{
  "projection_ref": "<projection_ref from run_projection>",
  "account_tax_treatment": "pre_tax",
  "marginal_ordinary_rate": 0.22,
  "ltcg_rate": 0.15
}
```

The final-month spendable values come back inline in `final_balance_percentiles` (`pre_tax_cents` and `after_tax_cents` per percentile), with a pre-tax → after-tax line per percentile in `summary`. The full monthly `after_tax_percentiles` series is in the data file at `urls.data`. Query it with `jq` like any other data file.

The ref lasts as long as the projection's data file (about an hour). If it has expired, re-run `run_projection` and use the new ref.

## Usage notes

- **Use `run_projection`** for all projection needs — constant returns or time-varying.
- All money in **cents**. 10000000 = $100,000.
- Returns in **float decimals**. 0.07 = 7%.
- **Negative contributions = withdrawals**. No separate withdrawal parameter needed.
- **File-based responses**: All projections return URLs + compact inline summary. Use `jq` to query the data file for specific values.
- **After-tax projections**: Chain `run_projection` → `apply_after_tax_to_projection_result`, passing `projection_ref`, to get spendable values.
