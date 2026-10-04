# File-Based Responses

MCP tools that produce large datasets always write full results to a file server and return URLs + compact inline summary. This keeps large arrays (timeseries, Chart.js specs, amortization schedules) out of the LLM context window.

## Tools with file-based responses

| Tool                                      | Package    | Large data                              |
| ----------------------------------------- | ---------- | --------------------------------------- |
| `run_projection`                          | projection | Timeline with percentiles               |
| `run_projections`                         | projection | One `run_projection` response per entry |
| `project_plan`                            | projection | Whole-plan timeline with percentiles    |
| `compare_scenarios`                       | scenarios  | Side-by-side scenario projections       |
| `generate_mortgage_amortization_schedule` | mortgage   | Month-by-month schedule                 |
| `project_liability_payoff`                | liability  | Month-by-month paydown schedule         |
| `generate_projection_fan_chart`           | charts     | Chart.js chart spec                     |
| `generate_account_breakdown_chart`        | charts     | Chart.js chart spec                     |
| `generate_allocation_chart`               | charts     | Chart.js chart spec                     |
| `generate_projection_comparison_chart`    | charts     | Chart.js chart spec                     |
| `build_snapshot`                          | snapshot   | Point-in-time facts record              |
| `get_sample_profile`                      | state      | Complete sample state document          |
| `migrate_state`                           | state      | Migrated state document                 |

## Response format

```json
{
  "urls": {
    "data": "https://mcp.finplan.tools/files/abc123_data.json",
    "schema": "https://mcp.finplan.tools/files/abc123_schema.json"
  },
  "summary": {
    "time_horizon_months": 360,
    "final_balance_percentiles": {...},
    "interpretation": "..."
  }
}
```

- **`urls.data`**: Full JSON dataset — query it with `jq` or inject it into HTML
- **`urls.schema`**: Data dictionary describing field types, structure, and jq paths — read if needed
- **`summary`**: Key statistics extracted from the data (enough for most decisions)

Don't load data files into context — see [SKILL.md](../SKILL.md#data-files-stay-out-of-context).

## Workflow

1. Call the tool — response always includes URLs + compact summary
2. Use the inline **summary** for immediate insights/decisions
3. If you need to understand the data structure, read `urls.schema` or refer to inline schemas in [charts.md](charts.md) and [projection.md](projection.md)
4. If querying specific values, download `urls.data` to a local file and query it with `jq`
5. For **embedding data into HTML**, use the placeholder/inject pattern (see below and [charts.md](charts.md#html-rendering-workflow))

```bash
# Download the data file once (use the actual urls.data from the response)
mkdir -p "${TMPDIR:-/tmp}/finplan"
curl -s "<urls.data>" -o "${TMPDIR:-/tmp}/finplan/data.json"

# Extract specific values
jq '.percentile_timelines.p50[-1].total_value_cents' "${TMPDIR:-/tmp}/finplan/data.json"

# Get a range of months
jq '.percentile_timelines.p50[0:12]' "${TMPDIR:-/tmp}/finplan/data.json"

# Get p10 vs p90 range at final month
jq '{p10: .percentile_timelines.p10[-1].total_value_cents, p90: .percentile_timelines.p90[-1].total_value_cents}' "${TMPDIR:-/tmp}/finplan/data.json"
```

## Embedding data in self-contained HTML files

When building HTML files, embed data via the placeholder/inject pattern rather than writing arrays as JS literals:

1. **Write the HTML** with placeholder tokens where data should go (e.g., `__DATA_TOTAL_PORTFOLIO__`)
2. **Download each `urls.data` file** into one scratch directory, `${TMPDIR:-/tmp}/finplan/`, never the user's working directory: `mkdir -p "${TMPDIR:-/tmp}/finplan" && curl -s "<urls.data>" -o "${TMPDIR:-/tmp}/finplan/<file>"`.
3. **Run the inject script** to replace each placeholder with its downloaded file. Pass the HTML file, then one placeholder/file pair per token:

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
" dashboard.html \
  "__DATA_PLACEHOLDER_1__" "${TMPDIR:-/tmp}/finplan/scenario1_data.json" \
  "__DATA_PLACEHOLDER_2__" "${TMPDIR:-/tmp}/finplan/scenario2_data.json"
```

This keeps the data out of your context window entirely. You already know the data shapes from the inline schemas — use them to write correct JavaScript rendering code.

For the full HTML rendering workflow, see [charts.md](charts.md#html-rendering-workflow).

## Schema File Format

Each schema file (`{uid}_schema.json`) is auto-generated and contains:

- **`tool`**: Which MCP tool generated the data
- **`data_type`**: Category (projection, chart, amortization)
- **`notes`**: Conventions (e.g., "All monetary values in cents")
- **`structure`**: Recursive type description with `type`, `fields`, `element_shape`, `jq_path`, and `description` for each field
- **`jq_examples`**: Ready-to-use jq expressions for common queries

### Example schema (projection)

```json
{
  "tool": "run_projection",
  "data_type": "projection",
  "notes": ["All monetary values in cents (divide by 100 for dollars)"],
  "structure": {
    "type": "object",
    "fields": {
      "net_deposits": {
        "type": "array",
        "length": 361,
        "jq_path": ".net_deposits",
        "description": "Cumulative net deposits by month",
        "element_shape": {
          "type": "object",
          "fields": {
            "month": { "type": "int", "jq_path": ".net_deposits[0].month" },
            "net_deposits_cents": {
              "type": "int",
              "jq_path": ".net_deposits[0].net_deposits_cents"
            }
          }
        }
      },
      "percentile_timelines": {
        "type": "object",
        "jq_path": ".percentile_timelines",
        "description": "Per-percentile monthly time series keyed by pN"
      }
    }
  },
  "jq_examples": [
    {
      "description": "Get p50 final balance",
      "jq": ".percentile_timelines.p50[-1].total_value_cents"
    },
    {
      "description": "Get all p50 monthly values",
      "jq": "[.percentile_timelines.p50[].total_value_cents]"
    }
  ]
}
```
