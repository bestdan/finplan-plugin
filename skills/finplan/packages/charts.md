# Chart Tools

Chart.js chart generation for financial visualizations. All charts return Chart.js JSON configs for client-side rendering.

<!-- BEGIN GENERATED: tool-index charts -->

## Tool index

| Tool                                   | Description                                                                                                       | Parameters                                                                                                                                                   |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `generate_account_breakdown_chart`     | Generate a stacked area chart showing each account's contribution to total portfolio over time.                   | initial_balances, expected_annual_return, time_horizon_months, title?, show_total_line?                                                                      |
| `generate_allocation_chart`            | Generate a stacked area chart of asset allocation (stocks/bonds/cash) over time.                                  | allocations, months, title?                                                                                                                                  |
| `generate_projection_comparison_chart` | Generate a line chart comparing projections under different return assumptions side by side (not plan scenarios). | scenarios, time_horizon_months, percentile?, title?, inflation?                                                                                              |
| `generate_projection_fan_chart`        | Generate a fan chart with percentile bands (p10/p25/p50/p75/p90) for projection results.                          | initial_balance_cents, expected_annual_return, time_horizon_months, annual_volatility?, monthly_contribution_cents?, title?, show_deposits_line?, inflation? |

<!-- END GENERATED: tool-index charts -->

## Data handling rules

Don't load data files into context or hardcode their arrays in HTML/JS — see [SKILL.md](../SKILL.md#data-files-stay-out-of-context). Render chart data with the [HTML rendering workflow](#html-rendering-workflow) below.

## Tool notes

On `generate_projection_fan_chart` and `generate_projection_comparison_chart`, `inflation` defaults to 0.0; when > 0, chart values are in today's purchasing power.

### generate_projection_fan_chart

`annual_volatility` defaults to 0.15, `monthly_contribution_cents` to 0, `title` to "Portfolio Projection", and `show_deposits_line` (cumulative deposits) to true.

### generate_account_breakdown_chart

`initial_balances` is a dict of account name to cents: `{"401k": 10000000, "Roth IRA": 5000000}`. `show_total_line` defaults to true.

### generate_allocation_chart

For glide path visualization. `allocations` is a list of `{"stocks_pct": 90, "bonds_pct": 8, "cash_pct": 2}` entries, and `months` holds the corresponding month numbers.

### generate_projection_comparison_chart

Compares at one percentile (`percentile`, default 50). Each `scenarios` entry is `{name, initial_balance_cents, expected_annual_return, annual_volatility, monthly_contribution_cents}`.

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
