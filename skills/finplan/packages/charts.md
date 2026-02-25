# Chart Tools

Chart.js chart generation for financial visualizations. All charts return Chart.js JSON configs for client-side rendering with `new Chart(element.getContext('2d'), chartjs)`.

## Tools

### generate_projection_fan_chart

Percentile bands (p10/p25/p50/p75/p90) for projection results.

| Parameter                    | Type   | Description                                   |
| ---------------------------- | ------ | --------------------------------------------- |
| `initial_balance_cents`      | int    | Starting balance in cents                     |
| `expected_annual_return`     | float  | Expected return (0.07 = 7%)                   |
| `time_horizon_months`        | int    | Months to project                             |
| `annual_volatility`          | float  | Annual std dev (default: 0.15)                |
| `monthly_contribution_cents` | int    | Monthly contribution (default: 0)             |
| `title`                      | string | Chart title (default: "Portfolio Projection") |
| `show_deposits_line`         | bool   | Show cumulative deposits (default: true)      |

### generate_account_breakdown_chart

Stacked area chart showing portfolio composition by account over time.

| Parameter                | Type   | Description                                       |
| ------------------------ | ------ | ------------------------------------------------- |
| `initial_balances`       | dict   | `{"401k": 10000000, "Roth IRA": 5000000}` (cents) |
| `expected_annual_return` | float  | Expected return                                   |
| `time_horizon_months`    | int    | Months to project                                 |
| `title`                  | string | Chart title                                       |
| `show_total_line`        | bool   | Show total portfolio line (default: true)         |

### generate_allocation_chart

Stacked area chart of asset allocation (stocks/bonds/cash) over time. For glide path visualization.

| Parameter     | Type       | Description                                                |
| ------------- | ---------- | ---------------------------------------------------------- |
| `allocations` | list[dict] | `[{"stocks_pct": 90, "bonds_pct": 8, "cash_pct": 2}, ...]` |
| `months`      | list[int]  | Corresponding month numbers                                |
| `title`       | string     | Chart title                                                |

### generate_scenario_comparison_chart

Line chart comparing multiple scenarios at a specific percentile.

| Parameter             | Type       | Description                                                                                                  |
| --------------------- | ---------- | ------------------------------------------------------------------------------------------------------------ |
| `scenarios`           | list[dict] | Each: `{name, initial_balance_cents, expected_annual_return, annual_volatility, monthly_contribution_cents}` |
| `time_horizon_months` | int        | Months to project                                                                                            |
| `percentile`          | int        | Percentile to compare (default: 50)                                                                          |
| `title`               | string     | Chart title                                                                                                  |

## Rendering

All chart tools return a Chart.js configuration that can be rendered with: `new Chart(element.getContext('2d'), chartjs)`

## Data schema (inline reference)

All chart data files (`urls.data`) share this structure. **You do NOT need to read the data or schema files** — use this reference to write correct rendering code:

```json
{
  "success": true,
  "chart_type": "projection_fan_chart | account_breakdown_chart | allocation_chart | scenario_comparison_chart",
  "chartjs": {
    "type": "line",
    "data": {
      "labels": ["Month 0", "Month 1", "..."],
      "datasets": [
        {
          "label": "P50 (Median)",
          "data": [50000000, 50500000, "..."],
          "borderColor": "rgba(...)",
          "backgroundColor": "rgba(...)",
          "fill": "-1 | false"
        }
      ]
    },
    "options": {
      "responsive": true,
      "plugins": { "title": { "text": "..." }, "...": "..." },
      "scales": { "x": { "...": "..." }, "y": { "...": "..." } }
    }
  },
  "metadata": {
    "title": "...",
    "parameters": { "initial_balance_cents": 0, "time_horizon_months": 0, "...": "..." },
    "final_balance_summary": { "p10_cents": 0, "p50_cents": 0, "p90_cents": 0, "...": "..." }
  },
  "message": "Render with new Chart(element.getContext('2d'), chartjs)."
}
```

Key fields for rendering:

- **`chartjs`** — Pass directly to `new Chart(ctx, chartjs)` for immediate rendering
- **`metadata`** — Use for summary cards and labels (title, final balance statistics)
- **`message`** — Human-readable summary

## File-based responses

All chart tools return file URLs + compact inline summary. The full Chart.js spec is in the data file, while the inline summary contains chart metadata and key statistics.

```
result = generate_projection_fan_chart(
    initial_balance_cents=500_000_00,
    expected_annual_return=0.07,
    time_horizon_months=360,
)

# result["urls"]["data"] -> file path/URL to the full Chart.js spec (NEVER read into context)
# result["urls"]["schema"] -> data structure description (you don't need this; use inline schema above)
# result["summary"] -> chart metadata and key statistics (use this for decisions)
```

- **`summary`** contains chart metadata and final balance statistics — use for summary cards
- **`urls.data`** contains the full Chart.js chart spec — **NEVER read this with the Read tool**
- When embedding in HTML, use bash to inject data files directly (see [file-tools.md](file-tools.md))

See [file-tools.md](file-tools.md) for details on file-based responses and the HTML embedding workflow.
