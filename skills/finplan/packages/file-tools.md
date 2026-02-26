# File-Based Responses

MCP tools that produce large datasets always write full results to a file server and return URLs + compact inline summary. This keeps large arrays (timeseries, Chart.js specs, amortization schedules) out of the LLM context window.

## Tools with file-based responses

| Tool                                      | Package    | Large data                |
| ----------------------------------------- | ---------- | ------------------------- |
| `run_projection`                          | projection | Timeline with percentiles |
| `generate_mortgage_amortization_schedule` | mortgage   | Month-by-month schedule   |
| `generate_projection_fan_chart`           | charts     | Chart.js chart spec       |
| `generate_account_breakdown_chart`        | charts     | Chart.js chart spec       |
| `generate_allocation_chart`               | charts     | Chart.js chart spec       |
| `generate_scenario_comparison_chart`      | charts     | Chart.js chart spec       |

## Response format

```json
{
  "urls": {
    "data": "https://mcp.finplan.prethink.io/files/abc123_data.json",
    "schema": "https://mcp.finplan.prethink.io/files/abc123_schema.json"
  },
  "summary": {
    "time_horizon_months": 360,
    "final_balance_percentiles": {...},
    "interpretation": "..."
  }
}
```

- **`urls.data`**: Full JSON dataset — **NEVER load into context** (see [charts.md — data handling rules](charts.md#data-handling-rules))
- **`urls.schema`**: Data dictionary describing field types, structure, and jq paths — read if needed
- **`summary`**: Key statistics extracted from the data (enough for most decisions)

## Workflow

1. Call the tool — response always includes URLs + compact summary
2. Use the inline **summary** for immediate insights/decisions
3. If you need to understand the data structure, read `urls.schema` or refer to inline schemas in [charts.md](charts.md) and [projection.md](projection.md)
4. If querying specific values, use `jq` — do NOT load the full data file into context
5. For **embedding data into HTML**, use the placeholder/inject pattern (see below and [charts.md](charts.md#html-rendering-workflow))

```bash
# Use jq to extract specific values (do NOT cat or Read the whole data file)
jq '.percentile_timelines.p50[-1].total_value_cents' /tmp/finplan/{uid}_data.json

# Get a range of months
jq '.percentile_timelines.p50[0:12]' /tmp/finplan/{uid}_data.json

# Get p10 vs p90 range at final month
jq '{p10: .percentile_timelines.p10[-1].total_value_cents, p90: .percentile_timelines.p90[-1].total_value_cents}' /tmp/finplan/{uid}_data.json
```

**CRITICAL**: NEVER load data files into context. Use `jq` for targeted queries, or use inline summaries from tool responses.

## Embedding data in self-contained HTML files

When building HTML files, embed data via the placeholder/inject pattern — **never read data files into context or hardcode arrays as JS literals**:

1. **Write the HTML** with placeholder tokens where data should go (e.g., `__DATA_TOTAL_PORTFOLIO__`)
2. **Run a bash command** to replace each placeholder with the actual file contents:

```bash
python3 -c "
import sys
html_path = sys.argv[1]
with open(html_path) as f:
    html = f.read()
replacements = dict(zip(sys.argv[2::2], sys.argv[3::2]))
for placeholder, data_path in replacements.items():
    path = data_path.replace('file://', '') if data_path.startswith('file://') else data_path
    with open(path) as f:
        html = html.replace(placeholder, f.read())
with open(html_path, 'w') as f:
    f.write(html)
" dashboard.html \
  "__DATA_PLACEHOLDER_1__" "/tmp/finplan/{uid1}_data.json" \
  "__DATA_PLACEHOLDER_2__" "/tmp/finplan/{uid2}_data.json"
```

This keeps the data out of your context window entirely. You already know the data shapes from the inline schemas — use them to write correct JavaScript rendering code.

For chart styling, colors, and the full HTML rendering workflow, see [charts.md](charts.md#html-rendering-workflow).

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
