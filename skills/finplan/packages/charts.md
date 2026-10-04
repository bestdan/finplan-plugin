# Chart Tools

Chart.js chart generation for financial visualizations. All charts return Chart.js JSON configs for client-side rendering.

## Data handling rules

Don't load data files into context or hardcode their arrays in HTML/JS — see [SKILL.md](../SKILL.md#data-files-stay-out-of-context). Render chart data with the [HTML rendering workflow](#html-rendering-workflow) below.

## Tools

### generate_projection_fan_chart

Percentile bands (p10/p25/p50/p75/p90) for projection results.

| Parameter                    | Type   | Description                                                                                             |
| ---------------------------- | ------ | ------------------------------------------------------------------------------------------------------- |
| `initial_balance_cents`      | int    | Starting balance in cents                                                                               |
| `expected_annual_return`     | float  | Expected return (0.07 = 7%)                                                                             |
| `time_horizon_months`        | int    | Months to project                                                                                       |
| `annual_volatility`          | float  | Annual std dev (default: 0.15)                                                                          |
| `monthly_contribution_cents` | int    | Monthly contribution (default: 0)                                                                       |
| `title`                      | string | Chart title (default: "Portfolio Projection")                                                           |
| `show_deposits_line`         | bool   | Show cumulative deposits (default: true)                                                                |
| `inflation`                  | float  | Annual inflation rate as decimal (default: 0.0). When > 0, chart values are in today's purchasing power |

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

### generate_projection_comparison_chart

Line chart comparing projections under different return assumptions at a specific percentile.

| Parameter             | Type       | Description                                                                                                  |
| --------------------- | ---------- | ------------------------------------------------------------------------------------------------------------ |
| `scenarios`           | list[dict] | Each: `{name, initial_balance_cents, expected_annual_return, annual_volatility, monthly_contribution_cents}` |
| `time_horizon_months` | int        | Months to project                                                                                            |
| `percentile`          | int        | Percentile to compare (default: 50)                                                                          |
| `title`               | string     | Chart title                                                                                                  |
| `inflation`           | float      | Annual inflation rate as decimal (default: 0.0). When > 0, chart values are in today's purchasing power      |

## File-based responses

All chart tools return file URLs + compact inline summary. For example, `generate_projection_fan_chart` with these arguments:

```json
{
  "initial_balance_cents": 50000000,
  "expected_annual_return": 0.07,
  "time_horizon_months": 360
}
```

returns:

- **`summary`** — chart metadata and final balance statistics (use for summary cards and text)
- **`urls.data`** — full Chart.js chart spec (inject it; don't load it — see [data handling rules](#data-handling-rules))
- **`urls.schema`** — data dictionary with field types and jq paths (read if needed)

## Data schema (inline reference)

All chart data files (`urls.data`) share this structure. Use this as a quick reference, or read `urls.schema` for full details:

```json
{
  "success": true,
  "chart_type": "projection_fan_chart | account_breakdown_chart | allocation_chart | projection_comparison_chart",
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

Key fields:

- **`chartjs`** — Pass directly to `new Chart(ctx, chartjs)` for immediate rendering
- **`metadata`** — Use for summary cards and labels (title, final balance statistics)
- **`message`** — Human-readable summary

## HTML rendering workflow

**Choose the path before Step 1.** For a standard fan chart from simple inputs (initial balance, return, volatility, horizon, monthly contribution, inflation), call [`generate_projection_fan_chart`](#generate_projection_fan_chart) instead of running Steps 1–4: its data file carries a ready `chartjs` config with the p10–p90 and p25–p75 bands, the median line and, unless `show_deposits_line` is false, the net-deposits line. Download that file, write a page whose script is `const DATA = __DATA_CHART__;` followed by `new Chart(ctx, DATA.chartjs)`, and inject the file as in Step 5.

Follow Steps 1–6 when the chart must reflect `run_projection`'s richer inputs, or needs a layout that tool can't produce.

### Step 1: Run the projection

Call `run_projection(...)`. The response includes:

- **`summary`** — scalar statistics (final balance percentiles, inputs). Use these for text, cards, and labels.
- **`urls.data`** — HTTPS URL to the full time-series JSON. You download it in step 2 and inject it in step 5.
- **`urls.schema`** — HTTPS URL to the data dictionary. You can read this.

### Step 2: Save the data and schema files locally

Download the files so the injection script can read them:

```bash
mkdir -p "${TMPDIR:-/tmp}/finplan"
curl -s "https://mcp.finplan.tools/files/{uid}_data.json" -o "${TMPDIR:-/tmp}/finplan/projection_data.json"
curl -s "https://mcp.finplan.tools/files/{uid}_schema.json" -o "${TMPDIR:-/tmp}/finplan/projection_schema.json"
```

Use the actual URLs from `urls.data` and `urls.schema` in the tool response.

### Step 3: Read the schema to understand the data structure

Read the schema file (it's small) to confirm the field names and types you'll reference in your JS code:

```bash
jq '.structure.fields | keys' "${TMPDIR:-/tmp}/finplan/projection_schema.json"
```

The schema tells you exactly what's in the data file without reading it. For `run_projection`, the key fields are:

- `percentile_timelines.p10[].total_value_cents` — monthly balances per percentile (p10/p25/p50/p75/p90)
- `percentile_timelines.p50[].month` — month numbers (0, 1, 2, ...)
- `net_deposits[].net_deposits_cents` — cumulative deposits by month

### Step 4: Write the HTML with placeholder tokens

Write the HTML file using the Write tool. Put a **placeholder token** where the data should go, and write JS that reads the fields you confirmed in step 3:

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
</head>
<body>
  <canvas id="chart"></canvas>
  <script>
    const DATA = __DATA_PROJECTION__; // replaced with the JSON file in step 5
    const p50 = DATA.percentile_timelines.p50;
    // build datasets from p10..p90 and DATA.net_deposits, then: new Chart(ctx, config)
  </script>
</body>
</html>
```

### Step 5: Inject the data file into the HTML

Run the [inject script](file-tools.md#embedding-data-in-self-contained-html-files) with `output.html` as the HTML file and one placeholder/file pair: `"__DATA_PROJECTION__" "${TMPDIR:-/tmp}/finplan/projection_data.json"`.

### Step 6: Open

Open `output.html` in a browser.

The result is a self-contained HTML file with all data embedded inline. No runtime fetches needed (except Chart.js CDN).

## Styling

Chart colors, palettes and page design for the plugin's dashboard and scenario pages are defined with the commands that build those pages, not here.

See [file-tools.md](file-tools.md) for more on file-based responses and the injection workflow.
