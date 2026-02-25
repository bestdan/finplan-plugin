---
description: Generate an interactive HTML financial projection dashboard with goal-oriented Monte Carlo simulations and Chart.js charts
allowed-tools:
  - Bash(jq *)
  - Bash(open *)
  - Bash(python3 *)
  - WebFetch
  - Write
argument-hint: [output-filename]
---

# Generate Goal-Oriented Projection Dashboard

Generate a self-contained HTML financial projection dashboard organized by goals, with linked accounts bundled into each goal.

## Output file

Write to: `$ARGUMENTS` (default: `comprehensive_projection_update_$TIMESTAMP.html` if no argument given)

## Step 1: Read the user's state

Read the local state JSON file (look for `*_finplan_state.json` or `finplan_state.json` in the working directory). Extract:

- **Person**: name(s), age(s), income(s), dependents, marital status, filing status
- **Accounts**: each account's type, name, balance, allocation (stocks_pct/bonds_pct/cash_pct), and any notes
- **Goals**: each goal's name, type, target_date, target_amount, strategy, contributions, importance, status, linked_account_ids, and notes
- **Tax profile**: filing status and any relevant deductions

Calculate the current age from date_of_birth and today's date. Determine months from today to each goal's target_date.

## Step 2: Calculate portfolio characteristics

For each unique allocation found across accounts, call `calculate_portfolio_characteristics` to get the expected annual return and volatility. Also calculate the blended return/volatility for any post-retirement or post-goal allocation if specified in goal notes (e.g., a glide path target).

Store these as a lookup so accounts with the same allocation share characteristics.

## Step 3: Run projections per goal

**CRITICAL**: Each projection tool below returns file URLs + compact inline summary:

For each goal with a target_amount or target_date:

1. **Identify linked accounts** from `linked_account_ids` in the goal. Sum their current balances.
2. **Sum monthly contributions** for those accounts (from the goal's contribution_amount_cents or each account's known contribution rate).
3. **Call `run_projection`** with the combined balance, expected return, volatility, contribution, and months to the goal's target date.
4. **Record the percentile results** (p10, p25, p50, p75, p90) for the summary cards and to validate the chart.

For goals without linked accounts (e.g., unfunded goals), calculate the required monthly contribution using `calculate_monthly_contribution_needed` instead.

Also run a projection for the **total portfolio** (all investment accounts combined) to the end of the projection horizon (age 90).

## Step 4: Generate the HTML dashboard

Create a single self-contained HTML file using Chart.js (`https://cdn.jsdelivr.net/npm/chart.js@4`) with the following structure:

### Design system

- System fonts: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- Background: `#f0f2f5`
- Cards: white, `border-radius: 12px`, `box-shadow: 0 2px 8px rgba(0,0,0,0.08)`
- Responsive grid layout using CSS grid
- Mobile-friendly with `@media` breakpoints

### HTML structure

#### Header

- Title: "Financial Projection Dashboard"
- Subtitle with person names, date, and "Goal-Oriented Projection"

#### Summary cards (one per goal + total)

Each card shows:

- Goal name and current balance of linked accounts
- Key projection stat (median at target date, or target vs projected)
- Color-coded status badge:
  - **Green ("On Track")**: p25 meets or exceeds target, or no explicit target and trajectory is healthy
  - **Amber ("Needs Plan")**: goal has no funding, or p50 falls short of target
  - **Red ("At Risk")**: p50 falls significantly short of target
- Left border color matches status

#### Chart 1: Total Portfolio (full width)

- Lognormal fan chart with P10/P25/P50/P75/P90 bands
- X-axis: age (from current age to 90)
- Vertical dashed milestone lines for: retirement age, Social Security age, college years, or any other goal target dates
- Annotated milestone labels

#### Charts 2+: One chart per goal (2-column grid)

For each goal, generate the appropriate chart type:

**Retirement-type goals** (goal_type = "retirement"):

- Stacked area of linked accounts (each account a different color) showing their individual contribution to the combined total
- Fan chart bands (P10-P90) overlaid on the combined median line
- Milestone markers for retirement age and SS start age
- Use chained projections: accumulation phase (positive contributions) then retirement phase (negative contributions = withdrawals minus SS income)

**Target-amount goals** (goal_type = "education", "emergency_fund", "home_purchase", "major_purchase"):

- Fan chart of the linked account(s) balance over time
- Horizontal dashed target line at the target_amount
- Milestone markers for key dates (e.g., college start/end, purchase date)
- If the goal has a withdrawal phase (like college), show contributions stopping and withdrawals during that period

**Unfunded/gap-analysis goals** (no linked accounts, or current_balance = 0):

- Required savings path line (monthly contribution * months) from 0 to target
- Current progress line (flat at 0 or current balance)
- Star marker at the target amount and target date
- Annotated gap callout showing shortfall and required monthly contribution

#### Final chart: Account Breakdown (in the grid)

- Stacked area chart of ALL individual accounts over time to age 90
- Same milestone markers as the total portfolio chart
- Shows portfolio composition evolution

#### Assumptions section

- Grid of assumption groups covering: personal info, current balances, each goal's parameters, expected returns, volatility, key milestones

### Data from MCP tools (no client-side simulation)

**Do NOT reimplement projections in JavaScript.** All projection math is handled by the MCP tools. The HTML file renders pre-computed data.

**`run_projection(...)`** — returns `urls.data` with full monthly time series per percentile, `urls.schema` with the data dictionary, and `summary` with key statistics.

**You do NOT need `generate_projection_fan_chart`**. It runs its own projection internally (duplicating work) and returns a pre-built Chart.js config that doesn't support the custom layouts this dashboard needs (stacked accounts, milestone annotations, goal-specific colors). Use `run_projection` for everything — summary stats, chart data, and time series.

**Response structure** (from `run_projection`):

- `urls.data` — full time series dataset — **NEVER read this into context**
- `urls.schema` — data dictionary with field types and jq paths — **read this if you need to understand the data structure**
- `summary` — key statistics for immediate use (final balance percentiles, etc.)

#### CRITICAL: Do NOT read data files

**NEVER use the Read tool on data files.** Data files contain large time-series arrays (hundreds of KB). Reading them wastes tokens and makes the session extremely slow. You already have everything you need:

- **Summary cards**: Use the inline `summary` from each MCP tool response (contains percentile statistics, final balances, etc.)
- **Chart rendering code**: Read `urls.schema` if needed to confirm field names and types — or use the inline schemas below as a quick reference
- **Embedding data into HTML**: Use bash to inject file contents directly into the HTML (see below)

#### Data schemas (quick reference — or read `urls.schema` for full details)

**`run_projection` data file** (`urls.data`):

```json
{
  "inputs": { "initial_balance_cents": 50000000, "...": "..." },
  "outputs": { "final_balance_percentiles": { "p10": { "cents": 0, "dollars": 0 }, "...": "..." } },
  "summary": "...",
  "projection_result": { "scenario_id": "...", "iterations": 10000, "time_horizon_months": 360 },
  "net_deposits": [
    { "month": 0, "net_deposits_cents": 50000000 },
    { "month": 1, "net_deposits_cents": 50200000 }
  ],
  "percentile_timelines": {
    "p10": [
      { "month": 0, "total_value_cents": 50000000, "cumulative_investment_return_cents": 0 },
      "..."
    ],
    "p25": ["...same shape..."],
    "p50": ["...same shape..."],
    "p75": ["...same shape..."],
    "p90": ["...same shape..."]
  }
}
```

#### How to embed data into HTML

Write the HTML file with **placeholder tokens** where data should be injected, then use a **bash command** to replace each placeholder with the actual file contents. This keeps the data out of your context window entirely.

**Step 1**: Write the HTML using the Write tool with placeholder tokens:

```javascript
// In the HTML <script> block, use string placeholders for each data file:
const TOTAL_PORTFOLIO_DATA = __DATA_TOTAL_PORTFOLIO__;
const RETIREMENT_DATA = __DATA_RETIREMENT__;
const EDUCATION_DATA = __DATA_EDUCATION__;
// ... one constant per run_projection data file

// Build charts from the time series data:
// TOTAL_PORTFOLIO_DATA.percentile_timelines.p50[i].total_value_cents / 100
// TOTAL_PORTFOLIO_DATA.net_deposits[i].net_deposits_cents / 100
```

**Step 2**: Run a bash command to replace each placeholder with the actual data file:

```bash
python3 -c "
import sys, json
html_path = sys.argv[1]
with open(html_path) as f:
    html = f.read()
# Replace each placeholder with its data file contents
replacements = dict(zip(sys.argv[2::2], sys.argv[3::2]))
for placeholder, data_path in replacements.items():
    # Handle both file:// URIs and plain paths
    path = data_path.replace('file://', '') if data_path.startswith('file://') else data_path
    with open(path) as f:
        html = html.replace(placeholder, f.read())
with open(html_path, 'w') as f:
    f.write(html)
" OUTPUT_FILE.html \
  "__DATA_TOTAL_PORTFOLIO__" "/tmp/finplan/abc123_data.json" \
  "__DATA_RETIREMENT__" "/tmp/finplan/def456_data.json" \
  "__DATA_EDUCATION__" "/tmp/finplan/ghi789_data.json"
```

Use the actual `urls.data` paths returned by each MCP tool call (strip the `file://` prefix for local paths, or use HTTP URLs as-is with `urllib` if remote).

**Summary**: NEVER read `urls.data` files into context. Use `summary` for statistics, read `urls.schema` if you need to confirm data structure, and use bash to inject data files into the HTML.

### Chart.js chart conventions

- All charts: `{ responsive: true, maintainAspectRatio: false }`
- Interaction mode: `{ mode: 'index', intersect: false }`
- White backgrounds via CSS on canvas container
- Grid color: `#e5e7eb`
- Fan chart bands: use `fill: '-1'` with decreasing opacity from center (0.2 for p25-p75, 0.1 for outer bands)
- Milestone lines: dashed, color-coded per milestone type via annotation plugin
- Currency formatting: custom tick callback with `$` prefix and SI suffixes
- Legend: positioned at top

### Color palette for accounts

Assign distinct colors to each account. Suggested defaults:

- `#0ea5e9` (sky blue), `#8b5cf6` (purple), `#ec4899` (pink), `#f59e0b` (amber), `#10b981` (emerald), `#ef4444` (red), `#6366f1` (indigo)

### Color palette for goal fan charts

Each goal gets its own fan chart color:

- Retirement: green tones (`rgba(16, 185, 129, ...)`)
- Education/college: amber tones (`rgba(245, 158, 11, ...)`)
- Total portfolio: blue tones (`rgba(59, 130, 246, ...)`)
- Other goals: use remaining palette colors

## Step 5: Open the file

After writing the HTML file, open it in the user's browser with `open <filename>`.

## Important notes

- All monetary values from the state file and MCP tools are in **cents** — divide by 100 for dollar values in charts
- All projection math is handled by MCP tools; the HTML only renders pre-computed data
- If a goal has no linked_account_ids, check if accounts can be inferred from goal_type (e.g., retirement goals link to 401k/IRA accounts, education goals link to 529s)
- Retirement spending and Social Security amounts should be pulled from goal notes if available, or use reasonable defaults ($150k/yr spending, estimated SS from `estimate_social_security_pia_from_salary`)
- The file must be completely self-contained — embed all fetched data inline as JS constants (no external data dependencies except Chart.js CDN)
