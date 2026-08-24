---
name: finplan
description: Personal finance projection engine accessed via MCP tools. Use when helping users with financial projections, tax calculations, retirement planning, Social Security benefits, account management, goal planning, portfolio analysis, or mortgage calculations. All capabilities are accessed through MCP tools at https://mcp.finplan.tools/mcp — never call Python or CLI directly.
---

# FinPlan — Personal Finance Projection Engine

Future-focused projection engine accessed via MCP tools. Models current financial state and projects outcomes across scenarios, accounting for US tax law, goal priorities, and Monte Carlo uncertainty.

## Scope: planning, not investment advice

FinPlan is a financial **planning** engine. It is not an investment advisor, and you must not use it as one.

- **You may model** how an asset allocation, glidepath, expected return, or volatility assumption changes a plan's projected outcomes. "What happens to my plan at 80/20 instead of 60/40?" is exactly what this engine is for.
- **FinPlan is security-agnostic.** Allocation is asset-class only — stocks, bonds, cash, crypto, real estate, other. No tool accepts a ticker, and the engine knows nothing about any security's prospects.
- **Never judge a security's investment merit.** Don't say which stock or fund will do better, is over- or under-valued, or is the one to own. You have no basis for it, so any such answer would be invention.
- **But taxes on a specific holding are in scope.** A user's holdings matter to their plan, and you may reason about them **on the tax axis**: cost basis, unrealized gain, holding period, short- vs long-term treatment, the tax cost of realizing a gain. If they ask "should I sell A or B?", answer the tax half — "selling A realizes $8k of long-term gain at 15%, B realizes $20k short-term at your ordinary rate, so A costs about $4.2k less in tax" — and say plainly that which one is the better _investment_ is not something FinPlan can speak to. Answer the tax question; decline the merit question. Don't refuse the whole thing.
- **Do not prescribe an allocation either.** Model the allocations the user gives you and show what they do to the plan. Don't tell them which one is right for them.
- **Placeholders are fine, and are not advice.** A user who doesn't know their split shouldn't be blocked from planning — fill in a typical value so they can proceed, state clearly that it's a placeholder to be corrected later, and don't let it pass as a recommendation. An unblocked user with an approximate input is the goal; a user sent away to hunt for a statement is a failure.

Frame output as what the model _shows_, not what the user _should do_: "an 80/20 mix raises the projected median balance by $X and widens the 10th-percentile downside by $Y" — not "you should hold 80/20."

## How to use FinPlan

All interaction is through MCP tools served at:

```
https://mcp.finplan.tools/mcp
```

**Do NOT** call Python, import packages, or use the CLI. All capabilities are exposed as MCP tools.

## MCP conventions

- **Cold starts**: The MCP server may sleep after inactivity. Call `ping()` as a lightweight warm-up before doing real work — it takes no parameters and returns server status, version, and auth state. If it fails, wait 5-10 seconds and retry. The `/finplan:setup` flow handles this automatically.
- **Money inputs**: Cents (integer). `10000000` = $100,000.00
- **Money outputs**: Both `_cents` and `_dollars` fields returned
- **Displaying money**: Money values from tools are in cents. **Always reformat for display**: divide by 100 and format as `$X,XXX.XX` (e.g., `10000000` → `$100,000.00`). Use the `_dollars` field when available for convenience, but the `_cents` field is the canonical value
- **Rates/returns**: Float decimals. `0.07` = 7%, `0.15` = 15%
- **Percentages**: Integer 0-100 for allocations. Float 0.0-1.0 for rates
- **All tools return**: `success`, `summary`/`message`, plus detailed fields

## If MCP tools aren't available

If FinPlan tools don't appear in the deferred tools list (no `mcp__claude_ai_FinPlan` entries), the MCP connection failed to establish. Do NOT try to call MCP tools or curl the server directly — run `/finplan:diagnose` instead. It tests server reachability, authentication, and tool availability client-side and provides specific remediation steps.

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
# result["urls"]["schema"] -> data dictionary — read if you need to understand data structure
# result["summary"] -> key statistics (final balance percentiles) for immediate use
```

**CRITICAL**: NEVER load data files into context. This means:

- No `Read` tool on `*_data.json` files
- No `WebFetch` or `fetch()` on `urls.data` URLs
- No hardcoding data arrays extracted from tool responses as JS literals (e.g., `const p50 = [100, 101, ...]`)

All three do the same thing: push hundreds of KB of time-series data through the context window, wasting tokens and producing brittle output. Instead:

- **Use `summary`** from the tool response for statistics, percentile values, and decision-making
- **Use `urls.schema`** or inline schemas in [charts.md](packages/charts.md) to understand data structure
- **Use `jq`** for targeted queries when you need specific values from data files
- **Use the placeholder/inject pattern** for any HTML that renders chart data (see [charts.md](packages/charts.md#html-rendering-workflow))

**Tools with file-based responses**: `run_projection`, `generate_mortgage_amortization_schedule`, `project_liability_payoff`, `generate_projection_fan_chart`, `generate_account_breakdown_chart`, `generate_allocation_chart`, `generate_projection_comparison_chart`

See [packages/file-tools.md](packages/file-tools.md) for full details and the HTML embedding workflow.

## Tool categories

When working with a specific area, read its detailed reference for tool names, parameters, and usage:

| Category        | What it does                                            | Reference                                                  |
| --------------- | ------------------------------------------------------- | ---------------------------------------------------------- |
| Projections     | Monte Carlo, closed-form, return-assumption comparison  | [packages/projection.md](packages/projection.md)           |
| Scenarios       | Plan "what if" deltas: create, apply, compare scenarios | [packages/scenarios.md](packages/scenarios.md)             |
| Tax             | Federal + 50-state/DC + local income tax, capital gains | [packages/tax.md](packages/tax.md)                         |
| RMD             | Required Minimum Distributions, IRS tables, penalties   | [packages/rmd.md](packages/rmd.md)                         |
| Accounts        | Account types, allocations, ownership, creation         | [packages/accounts.md](packages/accounts.md)               |
| Portfolio       | Return assumptions, glide paths, characteristics        | [packages/portfolio.md](packages/portfolio.md)             |
| Goals           | Financial goals, contribution calc, progress tracking   | [packages/goals.md](packages/goals.md)                     |
| Social Security | Benefits, claiming strategies, spousal/survivor, PIA    | [packages/social-security.md](packages/social-security.md) |
| Mortgage        | Monthly payments, amortization, P&I splits              | [packages/mortgage.md](packages/mortgage.md)               |
| Liabilities     | Debt paydown trajectory + payoff date (cards, loans)    | [packages/liability.md](packages/liability.md)             |
| Employer Match  | 401(k) matching formulas, vesting, calculations         | [packages/employer-match.md](packages/employer-match.md)   |
| Charts          | Chart.js fan charts, account breakdowns, comparisons    | [packages/charts.md](packages/charts.md)                   |
| File Tools      | File-based responses, `generate_data` parameter         | [packages/file-tools.md](packages/file-tools.md)           |
| Profile & State | Person profiles, user state persistence                 | [packages/state.md](packages/state.md)                     |
| Snapshots       | Build point-in-time facts records, diff two snapshots   | [packages/snapshot.md](packages/snapshot.md)               |
| Tool Search     | Dynamic tool discovery, search across all tools         | [packages/tool-search.md](packages/tool-search.md)         |
| Reference Data  | Static lookup tables: account types, enums, limits      | [packages/reference-data.md](packages/reference-data.md)   |
| System          | Server ping, readiness check, auth verification         | [packages/system.md](packages/system.md)                   |

## State Persistence Guidelines

**CRITICAL**: User state must be persisted whenever information changes. Persistence is handled **client-side** via slash commands, not by the MCP server.

### Client-side commands

These commands are bundled with the FinPlan plugin and available automatically after installation. See [SETUP.md](SETUP.md) for installation instructions.

- **`/read-state`** — Read state from local JSON file using targeted `jq` queries (minimal token usage). Supports: `/read-state`, `/read-state person`, `/read-state accounts`, `/read-state goals`, `/read-state account <id>`, `/read-state goal <id>`.
- **`/save-state`** — Write the current state JSON to the local file system. Call after every state mutation.
- **`/projection-dashboard`** — Generate a self-contained HTML dashboard with goal-oriented Monte Carlo projections and interactive Chart.js charts.
- **`/profile`** — View and update the user's personal financial profile (age, income, employment, marital status, dependents).
- **`/accounts`** — View and manage financial accounts (balances, allocations, add/update accounts).
- **`/goals`** — View and manage financial goals with guided setup for common goal types (emergency fund, retirement, education, home, major purchase).
- **`/setup`** — Guided interview to create a complete financial profile, accounts, and goals from scratch.
- **`/checkup`** — Review an existing plan for life changes, update profile/accounts/goals, and identify gaps or new goals.

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
state = manage_state(action="create", ...)   # returns the full document
/finplan:save-state

account = create_account(...)
# update_* returns a compact delta by default, NOT the full document:
#   {success, message, changed: {section, item}, state_hash, last_updated}
delta = manage_state(action="update_account", state_json=state, account_json=account["account"])
state = apply_delta(state, delta)             # update-or-append changed.item into changed.section
/finplan:save-state

goal = create_goal(...)
delta = manage_state(action="update_goal", state_json=state, goal_json=goal["goal"])
state = apply_delta(state, delta)
/finplan:save-state
```

> **Mutation responses are deltas by default** (see PRE-134). `update_*` actions return only the changed section plus a `state_hash`, instead of echoing the whole 5–10 KB document back through context on every edit. You already hold the full state (you passed it in as `state_json`), so apply `changed.item` to the section named in `changed.section` to rebuild it — `/finplan:save-state` does this for you. Pass `return_full_state=true` if you need the complete document returned inline.

## Recommended workflows

**Quick projection**: Use `run_projection` for fast analytical projections with percentile outputs. This is the recommended default.

**New user setup**: Run `/finplan:setup` for a guided interview that creates the profile, adds accounts, and sets up goals.

**Full planning session**:

1. `/finplan:read-state` to load existing state (or skip if starting fresh)
2. `manage_state(action="create")` → `/finplan:save-state`
3. For each account: `create_account` → `manage_state(action="update_account")` → `/finplan:save-state`
4. For each goal: `create_goal` → `manage_state(action="update_goal")` → `/finplan:save-state`
5. `calculate_portfolio_characteristics` for return/volatility assumptions
6. `run_projection` for projections
7. `generate_projection_fan_chart` to visualize results

**Periodic review**: Run `/finplan:checkup` to review the plan for life changes, update values, and identify new goals.

**Quick updates**: Use `/finplan:profile`, `/finplan:accounts`, or `/finplan:goals` to view or update individual sections.

**Social Security analysis**:

1. `estimate_social_security_pia_from_earnings_record` to get a PIA from an SSA earnings record — the only tool that can express a stop-work year. `calculate_social_security_pia_from_aime` if the caller already has an AIME; `estimate_social_security_pia_from_salary` only as a flat-career fallback when no earnings record is available.
2. `compare_social_security_claiming_ages` for full claiming-age analysis (benefits, breakevens, life-expectancy sensitivity, household figures) in one call
3. Single-purpose tools (`estimate_social_security_benefits_all_ages`, `estimate_social_security_breakeven_age`, `calculate_social_security_lifetime_benefits`) for month-precision ages or auditing individual figures
