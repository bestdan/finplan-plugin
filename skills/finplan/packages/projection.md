# Projection Tools

Project investment growth with uncertainty using analytical or Monte Carlo methods.

**Terminology:**

- **Constant-return mode**: Input mode where you provide fixed `expected_annual_return` and `annual_volatility`
- **Timeline mode**: Input mode where you provide time-varying returns via `return_distribution_timeline` (glide paths)
- **Projection methods**: Computation approaches (`closed_form` = analytical, `monte_carlo` = simulation, `deterministic` = no uncertainty, `auto` = automatically select)

## Tools

### run_projection

Unified projection tool supporting both constant-return and time-varying (glide path) inputs.

**Two input modes:**

1. **Constant returns** — provide `expected_annual_return`, `annual_volatility`, and `time_horizon_months`. Supports `fees`, `inflation`, and custom `percentiles`.

2. **Time-varying returns** — provide `return_distribution_timeline` with monthly entries for glide paths. The time horizon is derived from the timeline length.

| Parameter                      | Type       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `initial_balance_cents`        | int        | Starting balance in cents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `expected_annual_return`       | float      | Expected annual return (0.07 = 7%). For constant-return mode.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `annual_volatility`            | float      | Annual std dev (0.15 = 15%). For constant-return mode.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `time_horizon_months`          | int        | Months to project. Required for constant-return mode.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `return_distribution_timeline` | list[dict] | Monthly entries: `{month, return, volatility}`. For timeline mode.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `monthly_contribution_cents`   | int        | Constant monthly contribution in cents (default: 0). Negative = withdrawal. In retirement mode this is the pre-retirement (accumulation) contribution. Mutually exclusive with `contribution_timeline`.                                                                                                                                                                                                                                                                                                                                                     |
| `contribution_timeline`        | list[dict] | Explicit per-month contributions: `{month, contribution_cents}` (1-indexed, sequential, one entry per month of the horizon). Positive = contribution, negative = withdrawal. Mutually exclusive with `monthly_contribution_cents` and `retirement_month`.                                                                                                                                                                                                                                                                                                   |
| `retirement_month`             | int        | 1-indexed month at which contributions flip to withdrawals (accumulation -> decumulation) in a single call. Mutually exclusive with `contribution_timeline`.                                                                                                                                                                                                                                                                                                                                                                                                |
| `retirement_withdrawal_cents`  | int        | Gross monthly withdrawal in cents from `retirement_month` onward (>= 0, default: 0). Requires `retirement_month`.                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `retirement_income_cents`      | int        | Monthly income in cents (e.g. Social Security) offsetting the withdrawal from `retirement_month` onward (>= 0, default: 0). Requires `retirement_month`.                                                                                                                                                                                                                                                                                                                                                                                                    |
| `method`                       | string     | `"closed_form"` (default), `"auto"`, `"deterministic"`, `"monte_carlo"`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `iterations`                   | int        | Monte Carlo iterations (default: 1000)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `seed`                         | int        | Random seed for reproducibility                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `fees`                         | list[dict] | Optional list of fee specs, e.g. `[{"type": "flat_percent", "annual_rate": 0.005}]` (percent of AUM) or `[{"type": "flat_dollar", "annual_amount_cents": 500000}]` (fixed dollars/year). Stackable. A `flat_dollar` fee also takes `price_level`: `"nominal"` (default) is an unindexed contract amount, so its real cost falls as prices rise; `"real"` is a today's-dollars amount that tracks inflation and holds its purchasing power. Two `flat_dollar` fees in different price levels are rejected — they sum into one rail, which carries one frame. |
| `inflation`                    | float      | Annual inflation rate (0.03 = 3%, default: 0.025). 0 gives nominal dollars. Constant-return mode only.                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `percentiles`                  | list[int]  | Percentiles to compute (default: [10, 25, 50, 75, 90]). Constant-return mode only.                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `cumulative_volatility`        | bool       | For `method="closed_form"` only (ignored otherwise). If True (default), volatility compounds cumulatively over time (scales with sqrt(T)), widening percentile spreads as the horizon grows. If False, uses average per-period volatility (~constant spreads) and keeps a projection with cashflows on the analytic form, which is less accurate in the tails.                                                                                                                                                                                              |
| `summary_only`                 | bool       | When True, skip the per-month time-series data file and return only the inline summary (final_balance_percentiles + scalar metadata). Use for headline-only reads like per-account breakdown tables to avoid a file artifact per call. Default False keeps the full timeline.                                                                                                                                                                                                                                                                               |

Provide **either** constant-return params **or** `return_distribution_timeline`, not both.

Each timeline entry: `{"month": 1, "return": 0.07, "volatility": 0.15}` (1-indexed, sequential).

**Response**: Always returns file URLs + compact inline summary. The inline summary contains `final_balance_percentiles` (p10/p25/p50/p75/p90 in cents) and scalar metadata. Full time series is in the data file only.

**Data file**: All monetary values in **cents** (divide by 100 for dollars). Contains `net_deposits` (top-level, shared across percentiles) and `percentile_timelines` with per-percentile monthly snapshots containing `total_value_cents` and `cumulative_investment_return_cents`.

### run_projections

Batch/vectorized `run_projection`: run many independent projections in **one call**, fanned out in parallel. Use this instead of N serial `run_projection` calls whenever you have several same-shape, independent projections (a per-account retirement breakdown, one chart series per allocation, etc.).

| Parameter     | Type       | Description                                                                                                                                                                                                                                    |
| ------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `projections` | list[dict] | List of independent projections to run. Each entry is a `run_projection` parameter object — at minimum `{initial_balance_cents}` plus either constant-return params or a `return_distribution_timeline`, and any other `run_projection` param. |

**Response**: `{success, count, succeeded, failed, projections}`. `projections` holds one result per input entry, **in the same order**; each successful element has the same shape `run_projection` returns (file URLs + compact summary). A malformed entry yields a per-entry `{success: false, error, message}` in its slot without failing the others. Up to 50 projections per call.

### compare_return_assumptions

Compare market outcomes under conservative (5%/8%), moderate (7%/15%), and aggressive (9%/22%) return assumptions.

| Parameter               | Type  | Description                                                                                                                   |
| ----------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------- |
| `initial_balance_cents` | int   | Starting balance in cents                                                                                                     |
| `years`                 | int   | Years to project (default: 30)                                                                                                |
| `num_simulations`       | int   | Simulations per assumption set (default: 1000)                                                                                |
| `inflation`             | float | Annual inflation rate as decimal (default: 0.025). When > 0, results are in today's purchasing power; 0 gives nominal dollars |

### project_plan

Project a whole household plan: decompose `UserState` accounts into per-account projections and aggregate them into one after-tax outcome. Each account is projected with its own allocation → return distribution; the household net monthly surplus (income − expenses) is fed in as contributions split by balance; per-account withdrawal tax treatment yields after-tax spendable values. Liability and real-estate accounts are reported under `skipped_accounts`, not projected. Supply either the full `state_json` or a live `state_ref`; inline state takes precedence. The response returns `summary.inputs.base_state_ref`, reusable as `state_ref` while live. Refs have an approximately 60-minute sliding TTL that refreshes on each use; on `state_ref_expired`, re-send the full `state_json` in that same call.

| Parameter                 | Type      | Description                                                                                                                                                                                   |
| ------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `state_json`              | object    | A full UserState document as JSON (accounts, income_streams, and expenses drive the whole-plan projection). Required unless `state_ref` is supplied; takes precedence when both are given.    |
| `state_ref`               | string    | A live `st_…` state handle returned by another tool; use it instead of `state_json` to avoid re-sending the full document.                                                                    |
| `time_horizon_months`     | int       | Number of months to project (default: 360 = 30 years).                                                                                                                                        |
| `assumptions_preset`      | string    | Capital-market assumptions applied to every account's allocation: `"standard"` (default), `"conservative"`, or `"optimistic"`.                                                                |
| `inflation`               | float     | Annual inflation rate as a decimal (default: 0.025). When > 0, values are in today's purchasing power (real); 0 gives nominal dollars.                                                        |
| `marginal_ordinary_rate`  | float     | Household marginal ordinary income tax rate for after-tax values (default: 0.22).                                                                                                             |
| `ltcg_rate`               | float     | Household long-term capital gains tax rate for after-tax values (default: 0.15).                                                                                                              |
| `percentiles`             | list[int] | Percentiles to compute (default: [10, 25, 50, 75, 90]).                                                                                                                                       |
| `method`                  | string    | `"closed_form"` (default), `"auto"`, `"deterministic"`, `"monte_carlo"`.                                                                                                                      |
| `iterations`              | int       | Monte Carlo iterations (default: 1000, only used for `method="monte_carlo"`).                                                                                                                 |
| `seed`                    | int       | Random seed (only used for `method="monte_carlo"`).                                                                                                                                           |
| `invest_residual_surplus` | bool      | Whether the household surplus left over after account contribution pins is invested across the remaining accounts by balance (default: true). Set false to hold the leftover out of the plan. |

Accounts are projected independently and aggregated by summing matching percentiles (a perfectly-correlated / comonotonic assumption), surfaced in the response `assumptions` block.

An account contribution pin (a current-employer 401(k)'s employee deferral) is honored first; a configured `employer_match` on that plan is computed on the employee contribution and the household's annual W-2 compensation and routed on top (reported per account as `monthly_employer_match_cents`), so employer money compounds instead of being folded into one undifferentiated surplus. Income tax on wages is not modeled inside the projection.

**Response**: file URLs + compact inline summary (per-account headline figures, skipped accounts, household final pre/after-tax balances, assumptions). The full per-account and household time series live in the data file.

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
