# Projection Tools

Project investment growth with uncertainty using analytical or Monte Carlo methods.

**Terminology:**

- **Constant-return mode**: Input mode where you provide fixed `expected_annual_return` and `annual_volatility`
- **Timeline mode**: Input mode where you provide time-varying returns via `return_distribution_timeline` (glide paths)
- **Projection methods**: Computation approaches (`closed_form` = Kan & Zhou analytical, `monte_carlo` = simulation, `deterministic` = no uncertainty, `auto` = automatically select)

## Tools

### run_projection

Unified projection tool supporting both constant-return and time-varying (glide path) inputs.

**Two input modes:**

1. **Constant returns** — provide `expected_annual_return`, `annual_volatility`, and `time_horizon_months`. Supports `annual_fee`, `inflation`, and custom `percentiles`. Uses Kan & Zhou analytical methodology.

2. **Time-varying returns** — provide `return_distribution_timeline` with monthly entries for glide paths. The time horizon is derived from the timeline length.

| Parameter                      | Type       | Description                                                                        |
| ------------------------------ | ---------- | ---------------------------------------------------------------------------------- |
| `initial_balance_cents`        | int        | Starting balance in cents                                                          |
| `expected_annual_return`       | float      | Expected annual return (0.07 = 7%). For constant-return mode.                      |
| `annual_volatility`            | float      | Annual std dev (0.15 = 15%). For constant-return mode.                             |
| `time_horizon_months`          | int        | Months to project. Required for constant-return mode.                              |
| `return_distribution_timeline` | list[dict] | Monthly entries: `{month, return, volatility}`. For timeline mode.                 |
| `monthly_contribution_cents`   | int        | Monthly contribution in cents (default: 0)                                         |
| `method`                       | string     | `"closed_form"` (default), `"auto"`, `"deterministic"`, `"monte_carlo"`            |
| `iterations`                   | int        | Monte Carlo iterations (default: 1000)                                             |
| `seed`                         | int        | Random seed for reproducibility                                                    |
| `annual_fee`                   | float      | Annual fee as decimal (0.005 = 0.5%, default: 0). Constant-return mode only.       |
| `inflation`                    | float      | Annual inflation rate (0.03 = 3%, default: 0). Constant-return mode only.          |
| `percentiles`                  | list[int]  | Percentiles to compute (default: [10, 25, 50, 75, 90]). Constant-return mode only. |

Provide **either** constant-return params **or** `return_distribution_timeline`, not both.

Each timeline entry: `{"month": 1, "return": 0.07, "volatility": 0.15}` (1-indexed, sequential).

**Response**: Always returns file URLs + compact inline summary. The inline summary contains `final_balance_percentiles` (p10/p25/p50/p75/p90 in cents) and scalar metadata. Full time series is in the data file only.

**Data file**: All monetary values in **cents** (divide by 100 for dollars). Contains `net_deposits` (top-level, shared across percentiles) and `percentile_timelines` with per-percentile monthly snapshots containing `total_value_cents` and `cumulative_investment_return_cents`.

### compare_investment_scenarios

Compare conservative (5%/8%), moderate (7%/15%), and aggressive (9%/22%) scenarios.

| Parameter               | Type | Description                              |
| ----------------------- | ---- | ---------------------------------------- |
| `initial_balance_cents` | int  | Starting balance in cents                |
| `years`                 | int  | Years to project (default: 30)           |
| `num_simulations`       | int  | Simulations per scenario (default: 1000) |

## Working with file-based responses

The response always includes URLs + compact inline summary. The inline summary contains key statistics for immediate use. Full time series data is in the data file.

```
result = run_projection(
    initial_balance_cents=500_000_00,
    expected_annual_return=0.07,
    annual_volatility=0.15,
    time_horizon_months=360,
    monthly_contribution_cents=200_000,
)

# result["urls"]["data"] -> full time series JSON — NEVER read into context
# result["urls"]["schema"] -> data dictionary — read if you need to confirm field names
# result["summary"] -> final balance percentiles, inputs, method info
```

**CRITICAL**: NEVER load data files into context. See [charts.md — data handling rules](charts.md#data-handling-rules) for the full policy. Use `summary` for statistics, `jq` for targeted queries. The data file schema is:

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
# Use jq to extract specific values (NEVER Read the data file)
jq '.percentile_timelines.p50[-1].total_value_cents' /tmp/finplan/{uid}_data.json
jq '{p10: .percentile_timelines.p10[-1].total_value_cents, p90: .percentile_timelines.p90[-1].total_value_cents}' /tmp/finplan/{uid}_data.json
jq '.net_deposits[12].net_deposits_cents' /tmp/finplan/{uid}_data.json
```

For embedding data in HTML dashboards, use bash to inject file contents directly — see [file-tools.md](file-tools.md).

## Withdrawals (Retirement Phase)

**Negative contributions work as withdrawals.** To model retirement or any spending phase, use a negative `monthly_contribution_cents`:

```
run_projection(
    initial_balance_cents=500_000_00,      # $500k retirement savings
    monthly_contribution_cents=-4_000_00,  # $4,000/month withdrawal
    expected_annual_return=0.05,
    annual_volatility=0.10,
    time_horizon_months=360                # 30-year retirement
)
```

### Multi-phase planning (accumulation -> retirement)

Chain projections for different life phases:

1. **Accumulation phase** (positive contributions):
   ```
   accumulation = run_projection(
       initial_balance_cents=100_000_00,
       monthly_contribution_cents=2_000_00,  # Save $2k/month
       expected_annual_return=0.07,
       annual_volatility=0.15,
       time_horizon_months=240               # 20 years to retirement
   )
   ```

2. **Retirement phase** (negative contributions = withdrawals):
   ```
   retirement = run_projection(
       initial_balance_cents=accumulation["final_balance_percentiles"]["p50"]["cents"],
       monthly_contribution_cents=-5_000_00,  # Withdraw $5k/month
       expected_annual_return=0.05,
       annual_volatility=0.10,
       time_horizon_months=360                # 30-year retirement
   )
   ```

## After-tax projections

To compute after-tax spendable values from a projection, use `apply_after_tax_to_projection_result` (in the [Tax tools](tax.md)):

1. Run `run_projection` to get pre-tax results
2. Pass the result to `apply_after_tax_to_projection_result` with the account's tax treatment and the user's tax rates

```
projection = run_projection(
    initial_balance_cents=500_000_00,
    expected_annual_return=0.07,
    annual_volatility=0.15,
    time_horizon_months=360
)

after_tax = apply_after_tax_to_projection_result(
    projection_result_json=projection,
    account_tax_treatment="pre_tax",       # Traditional 401k/IRA
    marginal_ordinary_rate=0.22,
    ltcg_rate=0.15
)
# after_tax["adjusted_result"]["after_tax_percentiles"] has spendable values
```

## Usage notes

- **Use `run_projection`** for all projection needs — constant returns or time-varying.
- All money in **cents**. 10000000 = $100,000.
- Returns in **float decimals**. 0.07 = 7%.
- **Negative contributions = withdrawals**. No separate withdrawal parameter needed.
- **File-based responses**: All projections return URLs + compact inline summary. Use `jq` to query the data file for specific values.
- **After-tax projections**: Chain `run_projection` → `apply_after_tax_to_projection_result` to get spendable values.
