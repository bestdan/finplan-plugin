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
- **Accounts**: each account's `account_type`, `name`, `balance_cents`, allocation (stocks_pct/bonds_pct/cash_pct/crypto_pct/real_estate_pct/other_pct), `goal_id` (the goal this account funds, if any), and `notes`
- **Goals**: each goal's `id`, `name`, `goal_type`, `target_amount_cents`, `target_date`, `contribution_amount_cents` / `contribution_percentage`, `importance`, `status`, and `notes`
- **Tax profile**: filing status and any relevant deductions

Calculate the current age from date_of_birth and today's date. Determine months from today to each goal's target_date.

### Resolve the goal ↔ account linkage (direction matters)

The earmark link lives on the **account**, not the goal: each `Account` carries an optional `goal_id` naming the `Goal` it funds (whole-account, many-accounts-to-one-goal). A freshly-serialized state **omits the key** for an unlinked account, but a manually-edited or older file may instead carry `goal_id: null` — the core earmark logic treats **both** (absent key and explicit `null`) as unlinked, so handle them the same. There is **no** `linked_account_ids` field on a `Goal` in this schema — reading one back returns nothing, which is why an account-balance-by-goal pass built on it comes back all-null.

So build the grouping by scanning **accounts**: a goal's linked accounts are every account whose `goal_id` equals that goal's `id` (this is the one linkage rule Step 3b uses too); accounts with no `goal_id` are unearmarked (household-general, not tied to a single goal). The goal `id` is extracted in Step 1 only so you have something to match each account's `goal_id` against — not because the goal carries the link. If you are ever unsure of the current field names or direction, call `describe_state_schema` — it is the authority for what the loaded state actually contains.

## Step 2: Calculate portfolio characteristics

For each unique allocation found across accounts, call `calculate_portfolio_characteristics` to get the expected annual return and volatility. Also calculate the blended return/volatility for any post-retirement or post-goal allocation if specified in goal notes (e.g., a glide path target).

Store these as a lookup so accounts with the same allocation share characteristics.

## Step 3: Run the projections

**CRITICAL**: `run_projection` and `project_plan` return file URLs + a compact inline summary; `project_goal_progress` returns inline scalar percentiles only (no `urls.*` fields).

### 3a. Household / total line — one `project_plan(state)` call (the default)

Base the dashboard's household total (the full-width Total Portfolio chart and the "total" summary card) on a **single `project_plan(state_json=state)` call**, not a hand-rolled sum of per-goal or per-account `run_projection` runs. `project_plan` projects the **whole state** in one pass:

- each account grows on its own allocation's return/volatility;
- the household net monthly surplus (income − expenses) is fed in as contributions;
- withdrawal tax treatment is applied per account (pre-tax at the marginal rate, Roth/HSA/529 untaxed, taxable/crypto at LTCG) for after-tax spendable values;
- accounts are aggregated into household pre-tax and after-tax percentile timelines;
- each goal produces a per-goal outcome under `goal_outcomes` (projected balance/progress band + success probability at its target date), and non-evaluable goals land in `skipped_goals` with a reason.

This is cashflow-, income-, tax-, and retirement-aware and internally coherent, so it replaces the old "sum the per-account medians and hand-reconcile them against a blended retirement run" workflow — fewer calls, no manual reconciliation. Pass `time_horizon_months` for the horizon to age 90 — compute it as `(90 − current_age) * 12` using the primary person's age from Step 1 — plus `inflation` and the household `marginal_ordinary_rate` / `ltcg_rate` when known. Use its data file for the total-portfolio fan chart (`household_pre_tax_percentiles` / `household_after_tax_percentiles`, monthly time series keyed by percentile). Its **inline** `goal_outcomes` summaries carry only scalars per goal (`success_probability`, `meets_importance`, `return_basis`) — enough to cross-check each per-goal card's **success badge** cheaply; the full `projected_balance_percentiles` / `projected_progress_percentiles` **bands are file-only**, so cross-checking a card's band means reading them from the data file (jq/inject), not the inline summary. **Never read the data file into context** — use the placeholder/inject pattern (see below).

> Note: `project_plan`'s data file carries the household and per-account percentile timelines but **not** a `net_deposits` array. For the dashed net-deposits line on the total chart, compute it directly as initial balances + cumulative household contributions (preferred — keeps the call count down); only fall back to a `run_projection` of the combined portfolio if you need its exact `net_deposits` series.

### 3b. Per-goal isolated charts — `run_projection` + `project_goal_progress`

Reserve per-goal `run_projection` for the **isolated goal charts** (Charts 2+), where each goal is shown on its own. For each goal with a target_amount or target_date:

1. **Identify the goal's linked accounts** by filtering the state's accounts to those whose `goal_id` equals the goal's `id` (see "Resolve the goal ↔ account linkage" in Step 1 — the link is on the account, not the goal). Sum their current balances.
2. **Sum monthly contributions** for those accounts (from the goal's contribution_amount_cents or each account's known contribution rate).
3. **Call `run_projection`** with the combined balance, expected return, volatility, contribution, and months to the goal's target date.
4. **Record the percentile results** (p10, p25, p50, p75, p90) for the summary cards and to validate the chart.
5. **Call `project_goal_progress`** for the goal-native band: pass the goal JSON, the `annual_return_rate` and `annual_volatility` for the goal's allocation (from Step 2 — Calculate portfolio characteristics), `inflation`, and `monthly_income_cents` (the household monthly income from Step 1 — required so goals funded by `contribution_percentage` are projected correctly; harmless otherwise). Pass the allocation's **actual** volatility: a risk-bearing allocation spreads the result into `projected_balance_percentiles` and `projected_progress_percentiles` (p10/p25/p50/p75/p90), while a cash-like allocation with ~0 volatility collapses the band to the median (correct for a deterministic goal — don't fabricate a spread). Record the **progress band**: p10 (pessimistic), p50 (median), p90 (optimistic) fraction of target. This is the goal-aware "will I hit my target?" view that drives the status badge below; `run_projection` (step 3) drives the balance fan chart. (`project_plan`'s `goal_outcomes` computes the same band from the whole-plan pass, but only its `success_probability` scalar is inline — the band itself lives in `project_plan`'s data file; read it from there for a cross-check when the two disagree.)

For goals without linked accounts (e.g., unfunded goals), calculate the required monthly contribution using `calculate_monthly_contribution_needed` instead.

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
- **Progress band** — for goals with a positive `target_amount`, the goal-native pessimistic / median / optimistic fraction of target from `project_goal_progress`'s `projected_progress_percentiles`: render p10 / p50 / p90 (e.g. `48% · 71% · 96% of target`) so the uncertainty around hitting the goal is visible, not just a single number. The percentiles are fractions (e.g. `0.71` = 71%), so multiply by 100 for display. Optionally show the matching `projected_balance_percentiles` p10/p50/p90 underneath. **Skip the progress band for goals with no target_amount** (e.g. open-ended retirement) — core reports progress as `1.0` by definition there, so a band would show a meaningless 100/100/100; fall back to the "no explicit target" badge path below.
- Color-coded status badge, driven by the goal-native progress band (`projected_progress_percentiles`, compared as fractions against `1.0`). Evaluate as mutually exclusive, ordered branches so every goal lands in exactly one:
  - **Red ("At Risk")**: even the optimistic case falls short — `p90 < 1.0`.
  - else **Green ("On Track")**: the pessimistic case still meets the target — `p10 >= 1.0` (or no explicit target and the trajectory is healthy).
  - else **Amber ("Needs Plan")**: everything in between (the goal will likely hit its target in the median but is at risk in the downside), or the goal has no funding.
- Left border color matches status

#### Chart 1: Total Portfolio (full width)

- Lognormal fan chart with P10/P25/P50/P75/P90 bands
- X-axis: age (from current age to 90)
- Vertical dashed milestone lines for: retirement age, Social Security age, college years, or any other goal target dates
- Annotated milestone labels
- Dashed purple net deposits line showing total capital committed over time (initial balance + cumulative contributions)

#### Charts 2+: One chart per goal (2-column grid)

For each goal, generate the appropriate chart type:

**Retirement-type goals** (goal_type = "retirement"):

- Stacked area of linked accounts (each account a different color) showing their individual contribution to the combined total
- Fan chart bands (P10-P90) overlaid on the combined median line
- Dashed purple net deposits line showing total capital committed (initial balance + cumulative contributions)
- Milestone markers for retirement age and SS start age
- Use chained projections: accumulation phase (positive contributions) then retirement phase (negative contributions = withdrawals minus SS income)

**Target-amount goals** (goal_type = "education", "emergency_fund", "home_downpayment", "major_purchase"):

- Fan chart of the linked account(s) balance over time
- Horizontal dashed target line at the target_amount
- Dashed purple net deposits line showing total capital committed (initial balance + cumulative contributions)
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

**`project_plan(state_json=...)`** — the household/total default (Step 3a). Projects the whole state — every account on its own allocation, household surplus fed in as contributions, per-account withdrawal-tax treatment, aggregated into `household_pre_tax_percentiles` / `household_after_tax_percentiles` — in **one** call, plus per-goal `goal_outcomes`. Returns `urls.data` (household + per-account monthly time series), `urls.schema`, and a compact inline `summary` (scalars + per-account headline figures + goal-outcome summaries). Use this for the total-portfolio chart and the total card.

**`run_projection(...)`** — returns `urls.data` with full monthly time series per percentile, `urls.schema` with the data dictionary, and `summary` with key statistics. Use it for the **isolated per-goal charts** (Step 3b), and optionally for the total chart's `net_deposits` line (which `project_plan` does not emit — though you can compute net deposits directly instead; see Step 3a).

**`project_goal_progress(...)`** — the goal-native band for the summary cards. Pass `goal_json`, `annual_return_rate`, the allocation's actual `annual_volatility` (a risk-bearing allocation spreads the band; ~0 collapses it to the median), `inflation`, and `monthly_income_cents` (needed only for `contribution_percentage`-funded goals). Returns small inline scalars only (no file URLs): `projected_balance_percentiles` and `projected_progress_percentiles`, each as `{p10, p25, p50, p75, p90}` of fractions. Use the progress percentiles to render the per-goal progress band and drive the status badge; the headline `projected_progress_percentage` is the p50. Unlike `run_projection`, this accounts for the goal's own contributions, scheduled payouts, and inflation-adjusted target, so it answers "will this goal hit its target?" rather than "how does this lump grow?".

**You do NOT need `generate_projection_fan_chart`**. It runs its own projection internally (duplicating work) and returns a pre-built Chart.js config that doesn't support the custom layouts this dashboard needs (stacked accounts, milestone annotations, goal-specific colors). Build the household total from `project_plan` (Step 3a) and the isolated goal charts from `run_projection` (Step 3b) — summary stats, chart data, and time series all come from those tools' `summary` + data-file outputs.

**Response structure** (from `run_projection`, and analogously `project_plan`):

- `urls.data` — full time series dataset — **NEVER read this into context**
- `urls.schema` — data dictionary with field types and jq paths — **read this if you need to understand the data structure**
- `summary` — key statistics for immediate use (final balance percentiles, etc.)

#### CRITICAL: Do NOT read or inline data

**NEVER load data files into context** — no `Read` tool, no `WebFetch`, no hardcoded JS arrays. See [charts.md — data handling rules](../skills/finplan/packages/charts.md#data-handling-rules) for the full policy.

- **Summary cards**: Use `summary` from each MCP tool response (small scalar values, safe to use directly)
- **Chart rendering**: Use the inline schemas below or read `urls.schema` to confirm field names
- **Embedding data**: Use the placeholder/inject pattern below

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

**IMPORTANT — Net deposits must include the initial balance.** The `net_deposits` array
from `run_projection` already includes the starting account balance at month 0 — it is
NOT just cumulative contributions. Net deposits represents total capital committed
(initial balance + cumulative contributions over time). When building custom charts,
always use the pre-computed `net_deposits` data from `run_projection`. Never manually
calculate net deposits as only cumulative contributions starting from zero.

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

**Summary**: Use `summary` for statistics, placeholder tokens + bash injection for HTML data embedding.

### Chart styling

Follow the chart styling conventions in [charts.md](../skills/finplan/packages/charts.md#chart-styling) — colors, fonts, fan chart bands, account colors, goal colors, and page design are all defined there.

Dashboard-specific additions:

- Milestone lines: dashed, color-coded per milestone type via Chart.js annotation plugin

## Step 5: Open the file

After writing the HTML file, open it in the user's browser with `open <filename>`.

## Important notes

- All monetary values from the state file and MCP tools are in **cents** — divide by 100 for dollar values in charts
- All projection math is handled by MCP tools; the HTML only renders pre-computed data
- If no account carries a `goal_id` for a given goal (nothing earmarked to it), check if accounts can be inferred from goal_type (e.g., retirement goals link to 401k/IRA accounts, education goals link to 529s)
- Retirement spending and Social Security amounts should be pulled from goal notes if available, or use reasonable defaults ($150k/yr spending, estimated SS from `estimate_social_security_pia_from_earnings_record`, or `estimate_social_security_pia_from_salary` when no earnings record is on file)
- The file must be completely self-contained — embed all fetched data inline as JS constants (no external data dependencies except Chart.js CDN)
