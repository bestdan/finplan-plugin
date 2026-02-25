---
name: finplan
description: Personal finance projection engine accessed via MCP tools. Use when helping users with financial projections, tax calculations, retirement planning, Social Security benefits, account management, goal planning, portfolio analysis, or mortgage calculations. All capabilities are accessed through MCP tools at https://mcp.finplan.prethink.io/mcp — never call Python or CLI directly.
---

# FinPlan — Personal Finance Projection Engine

Future-focused projection engine accessed via MCP tools. Models current financial state and projects outcomes across scenarios, accounting for US tax law, goal priorities, and Monte Carlo uncertainty.

## How to use FinPlan

All interaction is through MCP tools served at:

```
https://mcp.finplan.prethink.io/mcp
```

**Do NOT** call Python, import packages, or use the CLI. All capabilities are exposed as MCP tools.

## MCP conventions

- **Money inputs**: Cents (integer). `10000000` = $100,000.00
- **Money outputs**: Both `_cents` and `_dollars` fields returned
- **Displaying money**: Money values from tools are in cents. **Always reformat for display**: divide by 100 and format as `$X,XXX.XX` (e.g., `10000000` → `$100,000.00`). Use the `_dollars` field when available for convenience, but the `_cents` field is the canonical value
- **Rates/returns**: Float decimals. `0.07` = 7%, `0.15` = 15%
- **Percentages**: Integer 0-100 for allocations. Float 0.0-1.0 for rates
- **All tools return**: `success`, `summary`/`message`, plus detailed fields

## File-Based Responses

Tools that produce large datasets always write full results to a file server and return URLs + compact inline summary. This keeps large arrays (timeseries, Chart.js specs, amortization schedules) out of the LLM context window.

```
# Example: 30-year projection
result = run_projection(
    initial_balance_cents=500_000_00,
    expected_annual_return=0.07,
    annual_volatility=0.15,
    time_horizon_months=360,
    monthly_contribution_cents=200_000,
)
# result["urls"]["data"] -> full time series JSON — NEVER read into context
# result["urls"]["schema"] -> data dictionary — usually not needed (use inline schemas in package docs)
# result["summary"] -> key statistics (final balance percentiles) for immediate use
```

**CRITICAL**: NEVER use the Read tool on data files (`*_data.json`). They contain large time-series arrays (hundreds of KB) that waste context tokens and make sessions extremely slow. Instead:

- **Use `summary`** from the tool response for statistics, percentile values, and decision-making
- **Use inline schemas** documented in [charts.md](packages/charts.md) and [file-tools.md](packages/file-tools.md) to understand data structure without reading files
- **Use `jq`** for targeted queries when you need specific values from data files
- **Use bash** to inject data into HTML files for dashboards (see [file-tools.md](packages/file-tools.md))

**Tools with file-based responses**: `run_projection`, `generate_mortgage_amortization_schedule`, `generate_projection_fan_chart`, `generate_account_breakdown_chart`, `generate_allocation_chart`, `generate_scenario_comparison_chart`

See [packages/file-tools.md](packages/file-tools.md) for full details and the HTML embedding workflow.

## Tool categories

When working with a specific area, read its detailed reference for tool names, parameters, and usage:

| Category        | What it does                                             | Reference                                                  |
| --------------- | -------------------------------------------------------- | ---------------------------------------------------------- |
| Projections     | Monte Carlo, closed-form, scenario comparison            | [packages/projection.md](packages/projection.md)           |
| Tax             | Federal income tax, capital gains, after-tax projections | [packages/tax.md](packages/tax.md)                         |
| RMD             | Required Minimum Distributions, IRS tables, penalties    | [packages/rmd.md](packages/rmd.md)                         |
| Accounts        | Account types, allocations, ownership, creation          | [packages/accounts.md](packages/accounts.md)               |
| Portfolio       | Return assumptions, glide paths, characteristics         | [packages/portfolio.md](packages/portfolio.md)             |
| Goals           | Financial goals, contribution calc, progress tracking    | [packages/goals.md](packages/goals.md)                     |
| Social Security | Benefits, claiming strategies, spousal/survivor, PIA     | [packages/social-security.md](packages/social-security.md) |
| Mortgage        | Monthly payments, amortization, P&I splits               | [packages/mortgage.md](packages/mortgage.md)               |
| Employer Match  | 401(k) matching formulas, vesting, calculations          | [packages/employer-match.md](packages/employer-match.md)   |
| Charts          | Chart.js fan charts, account breakdowns, comparisons     | [packages/charts.md](packages/charts.md)                   |
| File Tools      | File-based responses, `generate_data` parameter          | [packages/file-tools.md](packages/file-tools.md)           |
| Profile & State | Person profiles, user state persistence                  | [packages/state.md](packages/state.md)                     |
| Tool Search     | Dynamic tool discovery, search across all tools          | [packages/tool-search.md](packages/tool-search.md)         |
| Reference Data  | Static lookup tables: account types, enums, limits       | [packages/reference-data.md](packages/reference-data.md)   |

## State Persistence Guidelines

**CRITICAL**: User state must be persisted whenever information changes. Persistence is handled **client-side** via slash commands, not by the MCP server.

### Client-side commands

These commands are bundled with the FinPlan plugin and available automatically after installation. See [SETUP.md](SETUP.md) for installation instructions.

- **`/read-state`** — Read state from local JSON file using targeted `jq` queries (minimal token usage). Supports: `/read-state`, `/read-state person`, `/read-state accounts`, `/read-state goals`, `/read-state account <id>`, `/read-state goal <id>`.
- **`/save-state`** — Write the current state JSON to the local file system. Call after every state mutation.
- **`/projection-dashboard`** — Generate a self-contained HTML dashboard with goal-oriented Monte Carlo projections and interactive Chart.js charts.

### When to save state

Call `/finplan:save-state` immediately after ANY of these events:

- Creating a new user state
- Adding a new account to the state
- Adding a new goal to the state
- Updating person information (income, employment status, etc.)
- Modifying any account or goal details
- Any time the user provides new financial information

### How to maintain state

1. **Load state at session start** — Use `/finplan:read-state` to load existing state from local file
2. **Use state integration tools** — Use `manage_state(action="update_account")` and `manage_state(action="update_goal")` to integrate created objects
3. **Save after every change** — Call `/finplan:save-state` immediately after each modification. Don't batch saves.
4. **Use a consistent file path** — Default: `./finplan_state.json`

### Common mistake to avoid

❌ **Wrong**: Create accounts and goals but never add them to state or save

```
state = manage_state(action="create", ...)   # Creates state
create_account(...)         # Creates account but it's lost!
create_goal(...)            # Creates goal but it's lost!
# User's accounts and goals are never persisted
```

✅ **Correct**: Use integration tools and save after each change

```
state = manage_state(action="create", ...)
/finplan:save-state

account = create_account(...)
state = manage_state(action="update_account", state_json=state, account_json=account["account"])
/finplan:save-state

goal = create_goal(...)
state = manage_state(action="update_goal", state_json=state, goal_json=goal["goal"])
/finplan:save-state
```

## Recommended workflows

**Quick projection**: Use `run_projection` for fast analytical projections with percentile outputs. This is the recommended default.

**Full planning session**:

1. `/finplan:read-state` to load existing state (or skip if starting fresh)
2. `manage_state(action="create")` → `/finplan:save-state`
3. For each account: `create_account` → `manage_state(action="update_account")` → `/finplan:save-state`
4. For each goal: `create_goal` → `manage_state(action="update_goal")` → `/finplan:save-state`
5. `calculate_portfolio_characteristics` for return/volatility assumptions
6. `run_projection` for projections
7. `generate_projection_fan_chart` to visualize results

**Social Security analysis**:

1. `estimate_social_security_pia_from_salary` to estimate PIA
2. `estimate_social_security_benefits_all_ages` to compare claiming ages
3. `estimate_social_security_breakeven_age` for claiming strategy
4. `calculate_social_security_lifetime_benefits` for total benefit comparison
