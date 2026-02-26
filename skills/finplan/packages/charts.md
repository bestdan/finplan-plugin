# Chart Tools

Chart.js chart generation for financial visualizations. All charts return Chart.js JSON configs for client-side rendering.

## Data handling rules

These rules apply to ALL chart and projection work — dashboards, ad-hoc charts, one-off visualizations, everything.

1. **NEVER read data files into context.** No `Read` tool, no `WebFetch`, no `fetch()` on `urls.data` URLs. These files are hundreds of KB and reading them wastes tokens.
2. **NEVER hardcode data arrays in HTML/JS.** Do not extract time-series values from tool responses and write them as JavaScript literals (e.g., `const p50 = [100.00, 101.47, ...]`). This is the same problem as reading the file — the data passes through your context.
3. **DO use `summary`** from tool responses for text, statistics, and summary cards (small scalar values).
4. **DO use the placeholder/inject pattern** for any HTML that renders chart data. Write HTML with placeholder tokens, then use a bash/python script to inject the data file contents. See [HTML rendering workflow](#html-rendering-workflow) below.

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

## File-based responses

All chart tools return file URLs + compact inline summary. The full Chart.js spec is in the data file, while the inline summary contains chart metadata and key statistics.

```
result = generate_projection_fan_chart(
    initial_balance_cents=500_000_00,
    expected_annual_return=0.07,
    time_horizon_months=360,
)

# result["urls"]["data"] -> full Chart.js spec JSON — NEVER read into context
# result["urls"]["schema"] -> data structure description — read if you need to confirm field names
# result["summary"] -> chart metadata and key statistics (use this for decisions)
```

- **`summary`** — chart metadata and final balance statistics (use for summary cards and text)
- **`urls.data`** — full Chart.js chart spec (**NEVER load into context** — see [data handling rules](#data-handling-rules) above)
- **`urls.schema`** — data dictionary with field types and jq paths (read if needed)

## Data schema (inline reference)

All chart data files (`urls.data`) share this structure. Use this as a quick reference, or read `urls.schema` for full details:

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

Key fields:

- **`chartjs`** — Pass directly to `new Chart(ctx, chartjs)` for immediate rendering
- **`metadata`** — Use for summary cards and labels (title, final balance statistics)
- **`message`** — Human-readable summary

## HTML rendering workflow

Follow these steps to generate any chart — ad-hoc, dashboard, or one-off visualization.

### Step 1: Run the projection

Call `run_projection(...)`. The response includes:

- **`summary`** — scalar statistics (final balance percentiles, inputs). Use these for text, cards, and labels.
- **`urls.data`** — HTTPS URL to the full time-series JSON. Do NOT read this URL.
- **`urls.schema`** — HTTPS URL to the data dictionary. You CAN read this.

### Step 2: Save the data and schema files locally

Download the files so the injection script can read them:

```bash
curl -s "https://mcp.finplan.prethink.io/files/{uid}_data.json" -o /tmp/finplan_projection_data.json
curl -s "https://mcp.finplan.prethink.io/files/{uid}_schema.json" -o /tmp/finplan_projection_schema.json
```

Use the actual URLs from `urls.data` and `urls.schema` in the tool response.

### Step 3: Read the schema to understand the data structure

Read the schema file (it's small) to confirm the field names and types you'll reference in your JS code:

```bash
cat /tmp/finplan_projection_schema.json | jq '.structure.fields | keys'
```

The schema tells you exactly what's in the data file without reading it. For `run_projection`, the key fields are:

- `percentile_timelines.p10[].total_value_cents` — monthly balances per percentile (p10/p25/p50/p75/p90)
- `percentile_timelines.p50[].month` — month numbers (0, 1, 2, ...)
- `net_deposits[].net_deposits_cents` — cumulative deposits by month

### Step 4: Write the HTML with placeholder tokens

Write the HTML file using the Write tool. Use a **placeholder token** where the data should go. Write JS that references the data structure you confirmed in step 3:

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
</head>
<body>
  <canvas id="chart"></canvas>
  <script>
    // Placeholder — will be replaced with actual JSON in step 5
    const DATA = __DATA_PROJECTION__;

    // Extract time series from the injected data
    const p50 = DATA.percentile_timelines.p50;
    const p10 = DATA.percentile_timelines.p10;
    const p90 = DATA.percentile_timelines.p90;
    const p25 = DATA.percentile_timelines.p25;
    const p75 = DATA.percentile_timelines.p75;
    const deposits = DATA.net_deposits;

    const labels = p50.map(s => (s.month / 12).toFixed(1));

    new Chart(document.getElementById('chart').getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          // Outer band upper boundary (invisible line)
          {
            label: 'p90',
            data: p90.map(s => s.total_value_cents / 100),
            borderColor: 'transparent', borderWidth: 0, pointRadius: 0,
            fill: false
          },
          // Outer band lower boundary (fills up to p90)
          {
            label: '10th–90th Percentile',
            data: p10.map(s => s.total_value_cents / 100),
            borderColor: 'transparent', borderWidth: 0, pointRadius: 0,
            fill: '-1', backgroundColor: 'rgba(59, 130, 246, 0.1)'
          },
          // Inner band upper boundary (invisible line)
          {
            label: 'p75',
            data: p75.map(s => s.total_value_cents / 100),
            borderColor: 'transparent', borderWidth: 0, pointRadius: 0,
            fill: false
          },
          // Inner band lower boundary (fills up to p75)
          {
            label: '25th–75th Percentile',
            data: p25.map(s => s.total_value_cents / 100),
            borderColor: 'transparent', borderWidth: 0, pointRadius: 0,
            fill: '-1', backgroundColor: 'rgba(59, 130, 246, 0.2)'
          },
          // Median line
          {
            label: 'Median (50th)',
            data: p50.map(s => s.total_value_cents / 100),
            borderColor: '#3b82f6', borderWidth: 2.5, pointRadius: 0,
            fill: false
          },
          // Net deposits reference line
          {
            label: 'Net Deposits',
            data: deposits.map(d => d.net_deposits_cents / 100),
            borderColor: '#8b5cf6', borderWidth: 2, borderDash: [5, 5],
            pointRadius: 0, fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          tooltip: {
            mode: 'index', intersect: false,
            itemSort: (a, b) => b.raw - a.raw
          },
          legend: { position: 'top', labels: { usePointStyle: true } }
        },
        scales: {
          x: { title: { display: true, text: 'Years' } },
          y: {
            title: { display: true, text: 'Portfolio Value' },
            beginAtZero: true,
            ticks: {
              callback: v => v >= 1e6 ? '$' + (v/1e6).toFixed(1) + 'M'
                : v >= 1e3 ? '$' + (v/1e3).toFixed(0) + 'k' : '$' + v
            }
          }
        }
      }
    });
  </script>
</body>
</html>
```

### Step 5: Inject the data file into the HTML

Replace the placeholder token with the actual data file contents using a bash script:

```bash
python3 -c "
import sys
html_path = sys.argv[1]
with open(html_path) as f:
    html = f.read()
replacements = dict(zip(sys.argv[2::2], sys.argv[3::2]))
for placeholder, data_path in replacements.items():
    with open(data_path) as f:
        html = html.replace(placeholder, f.read())
with open(html_path, 'w') as f:
    f.write(html)
" output.html \
  "__DATA_PROJECTION__" "/tmp/finplan_projection_data.json"
```

### Step 6: Open

```bash
open output.html
```

The result is a self-contained HTML file with all data embedded inline. No runtime fetches needed (except Chart.js CDN).

## Chart styling

Use these conventions for consistent styling across all charts. These match the theme defined in `finplan_core.plotting.theme`.

### Chart.js options

```javascript
{
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { position: 'top', labels: { usePointStyle: true } },
    tooltip: {
      mode: 'index',
      intersect: false,
      // Sort tooltip items highest-to-lowest value
      itemSort: (a, b) => b.raw - a.raw
    }
  }
}
```

### Font stack

```
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
```

### Grid and axes

- Grid color: `#e5e7eb`
- Y-axis currency formatting: custom tick callback with `$` prefix and SI suffixes (`$100k`, `$1.2M`)
- X-axis: years (months / 12) for projections

### Fan chart bands

- Outer band (p10-p90): `rgba(59, 130, 246, 0.1)` — fill between p90 (upper boundary) and p10 with `fill: '-1'`
- Inner band (p25-p75): `rgba(59, 130, 246, 0.2)` — fill between p75 (upper boundary) and p25 with `fill: '-1'`
- Median (p50): `#3b82f6`, `borderWidth: 2.5`, solid line
- Net deposits: `#8b5cf6` (purple), `borderWidth: 2`, dashed (`borderDash: [5, 5]`)
- All band boundary lines: `pointRadius: 0`, `borderColor: 'transparent'`

### Percentile colors (when shown individually)

| Percentile | Color      | Hex       |
| ---------- | ---------- | --------- |
| p90        | Emerald    | `#10b981` |
| p75        | Lt Emerald | `#34d399` |
| p50        | Blue       | `#3b82f6` |
| p25        | Orange     | `#f97316` |
| p10        | Red        | `#ef4444` |

### Account type colors (for stacked/breakdown charts)

| Account type         | Color  | Hex       |
| -------------------- | ------ | --------- |
| Traditional 401k/IRA | Blue   | `#3b82f6` |
| Roth accounts        | Green  | `#10b981` |
| Taxable brokerage    | Amber  | `#f59e0b` |
| HSA                  | Pink   | `#ec4899` |
| 529 Education        | Purple | `#8b5cf6` |
| Real estate          | Indigo | `#6366f1` |
| Cash/savings         | Gray   | `#6b7280` |

### Goal-specific fan chart colors

| Goal type       | Base color                   |
| --------------- | ---------------------------- |
| Retirement      | Green — `rgba(16, 185, 129)` |
| Education       | Amber — `rgba(245, 158, 11)` |
| Total portfolio | Blue — `rgba(59, 130, 246)`  |

### Multi-account palette (for ad-hoc charts with multiple series)

`#0ea5e9` (sky), `#8b5cf6` (purple), `#ec4899` (pink), `#f59e0b` (amber), `#10b981` (emerald), `#ef4444` (red), `#6366f1` (indigo)

### Page design (for full-page HTML output)

- Background: `#f0f2f5`
- Cards: white, `border-radius: 12px`, `box-shadow: 0 2px 8px rgba(0,0,0,0.08)`
- Responsive grid layout using CSS grid
- Mobile-friendly with `@media` breakpoints

See [file-tools.md](file-tools.md) for more on file-based responses and the injection workflow.
