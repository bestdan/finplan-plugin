---
name: finplan
description: Personal finance projection engine accessed via MCP tools. Use when helping users with financial projections, what-if scenarios, tax calculations, retirement planning, required minimum distributions, Social Security benefits, account management, employer 401(k) match, goal planning, budgets and cashflow, portfolio analysis, mortgages and other debt payoff, charts, financial snapshots, or syncing accounts from an aggregator. All capabilities are accessed through MCP tools at https://mcp.finplan.tools/mcp — never call Python or CLI directly.
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
- **Tax year**: `calculate_federal_tax_liability`, `calculate_amt`, `get_tax_parameters`, `analyze_roth_conversion`, `model_iso_exercise`, `model_nqso_exercise`, and `model_rsu_vest` accept `tax_year` 2026 only. `calculate_federal_income_tax`, `calculate_capital_gains_tax_rate`, and `calculate_payroll_tax` accept 2024-2026
- **All tools return**: `success`, `summary`/`message`, plus detailed fields

## When a call fails

A tool that runs and cannot do what was asked returns `success: false` with `error` (a short category) and `message` (what was wrong, usually naming the field). Some failures add `action` (the recovery step) or `errors` (one entry per rejected item). Read them, correct the input, and call again. Don't resend an identical call, and don't present any part of a failed result as an answer.

- **`state_ref_expired`**: the `st_…` handle lapsed (refs have a roughly 60-minute sliding TTL). Make the same call again with the full `state_json` in place of `state_ref`, as its `action` says.
- **A batch entry fails alone**: `run_projections` and `calculate_portfolio_characteristics_batch` put `{success: false, error, message}` in that entry's slot and still return the others. Check every entry.
- **Rejected before the tool runs**: a wrong type or a missing required parameter comes back as an MCP error, not a `success: false` result. Call `describe_finplan_tool` for the live schema and fix the arguments.

## If MCP tools aren't available

FinPlan tools carry one of three prefixes, depending on how the server was connected: `mcp__plugin_finplan_finplan__` (this plugin), `mcp__claude_ai_<connector name>__` (a claude.ai connector, where the middle part is whatever the user named it, e.g. `mcp__claude_ai_FinPlan__`), or `mcp__finplan__` (a `finplan` entry in a project `.mcp.json`, or added with `claude mcp add`). Whatever the prefix, a tool whose name ends in a FinPlan tool name such as `__ping` or `__search_finplan_tools` is a FinPlan tool. If no such tool appears in the tools or deferred tools list, the MCP connection failed to establish. Do NOT try to call MCP tools or curl the server directly — run `/finplan:diagnose` instead. It tests server reachability, authentication, and tool availability client-side and provides specific remediation steps.

## File-Based Responses

Tools that produce large datasets always write full results to a file server and return URLs + compact inline summary. This keeps large arrays (timeseries, Chart.js specs, amortization schedules) out of the LLM context window.

For example, a 30-year projection — `run_projection` with these arguments:

```json
{
  "initial_balance_cents": 50000000,
  "expected_annual_return": 0.07,
  "annual_volatility": 0.15,
  "time_horizon_months": 360,
  "monthly_contribution_cents": 200000
}
```

It returns `summary` (final balance percentiles and inputs — use these directly), `urls.schema` (the data dictionary — read it if you need the data structure), and `urls.data` (the full time series — see below).

### Data files stay out of context

**CRITICAL**: NEVER load data files into context. This means:

- No `Read` tool on `*_data.json` files
- No `WebFetch` or `fetch()` on `urls.data` URLs
- No hardcoding data arrays extracted from tool responses as JS literals (e.g., `const p50 = [100, 101, ...]`)

All three do the same thing: push hundreds of KB of time-series data through the context window, wasting tokens and producing brittle output. Instead:

- **Use `summary`** from the tool response for statistics, percentile values, and decision-making
- **Use `urls.schema`** or inline schemas in [charts.md](packages/charts.md) to understand data structure
- **Use `jq`** for targeted queries when you need specific values from data files
- **Use the placeholder/inject pattern** for any HTML that renders chart data (see [charts.md](packages/charts.md#html-rendering-workflow))

**Tools with file-based responses**: `run_projection`, `run_projections`, `project_plan`, `compare_scenarios`, `generate_mortgage_amortization_schedule`, `project_liability_payoff`, `generate_projection_fan_chart`, `generate_account_breakdown_chart`, `generate_allocation_chart`, `generate_projection_comparison_chart`, `build_snapshot`, `get_sample_profile`, `migrate_state`

See [packages/file-tools.md](packages/file-tools.md) for full details and the HTML embedding workflow.

## Tool categories

When working with a specific area, read its detailed reference for tool names, parameters, and usage. Each category reference (all but File Tools and Reference Data) opens with a tool index that lists every parameter of every tool (`p` required, `p?` optional, `a|b` exactly one of, `a|b?` at most one of); call `describe_finplan_tool` for types, defaults, and allowed values.

| Category        | What it does                                            | Reference                                                  |
| --------------- | ------------------------------------------------------- | ---------------------------------------------------------- |
| Projections     | Monte Carlo, closed-form, return-assumption comparison  | [packages/projection.md](packages/projection.md)           |
| Scenarios       | Plan "what if" deltas: create, apply, compare scenarios | [packages/scenarios.md](packages/scenarios.md)             |
| Tax             | Federal + 50-state/DC + local income tax, capital gains | [packages/tax.md](packages/tax.md)                         |
| RMD             | Required Minimum Distributions, IRS tables, penalties   | [packages/rmd.md](packages/rmd.md)                         |
| Accounts        | Account types, allocations, ownership, creation         | [packages/accounts.md](packages/accounts.md)               |
| Portfolio       | Return assumptions, glide paths, characteristics        | [packages/portfolio.md](packages/portfolio.md)             |
| Goals           | Financial goals, contribution calc, progress tracking   | [packages/goals.md](packages/goals.md)                     |
| Budget          | Income streams, expenses, budget summary, cashflow      | [packages/budget.md](packages/budget.md)                   |
| Social Security | Benefits, claiming strategies, spousal/survivor, PIA    | [packages/social-security.md](packages/social-security.md) |
| Mortgage        | Monthly payments, amortization, P&I splits              | [packages/mortgage.md](packages/mortgage.md)               |
| Liabilities     | Debt paydown trajectory + payoff date (cards, loans)    | [packages/liability.md](packages/liability.md)             |
| Employer Match  | 401(k) matching formulas, vesting, calculations         | [packages/employer-match.md](packages/employer-match.md)   |
| Charts          | Chart.js fan charts, account breakdowns, comparisons    | [packages/charts.md](packages/charts.md)                   |
| File Tools      | File-based responses: `urls` + inline summary           | [packages/file-tools.md](packages/file-tools.md)           |
| Profile & State | Person profiles, user state persistence, account sync   | [packages/state.md](packages/state.md)                     |
| Snapshots       | Build point-in-time facts records, diff two snapshots   | [packages/snapshot.md](packages/snapshot.md)               |
| Tool Search     | Dynamic tool discovery, search across all tools         | [packages/tool-search.md](packages/tool-search.md)         |
| Reference Data  | Static lookup tables: account types, enums, limits      | [packages/reference-data.md](packages/reference-data.md)   |
| System          | Server ping, readiness check, auth verification         | [packages/system.md](packages/system.md)                   |

## State Persistence Guidelines

**CRITICAL**: User state must be persisted whenever information changes. Persistence is handled **client-side** via slash commands, not by the MCP server.

### Client-side commands

These commands are bundled with the FinPlan plugin and available automatically after installation. For setup on other platforms, see https://docs.finplan.tools/setup/.

- **`/read-state`** — Read state from local JSON file using targeted `jq` queries (minimal token usage). Supports: `/read-state`, `/read-state person`, `/read-state accounts`, `/read-state goals`, `/read-state account <id>`, `/read-state goal <id>`.
- **`/save-state`** — Write the current state JSON to the local file system. Call after every state mutation.
- **`/projection-dashboard`** — Generate a self-contained HTML dashboard with goal-oriented Monte Carlo projections and interactive Chart.js charts.
- **`/profile`** — View and update the user's personal financial profile (age, income, employment, marital status, dependents).
- **`/accounts`** — View and manage financial accounts (balances, allocations, add/update accounts).
- **`/goals`** — View and manage financial goals with guided setup for common goal types (emergency fund, retirement, education, home, major purchase).
- **`/setup`** — Guided interview to create a complete financial profile, accounts, and goals from scratch.
- **`/checkup`** — Review an existing plan for life changes, update profile/accounts/goals, and identify gaps or new goals.

### How to maintain state

1. **Load state at session start** — Use `/finplan:read-state` to load existing state from the local file (default: `./finplan_state.json`).
2. **Integrate every object you create** — An account, goal, income stream, or expense made with a `create_*` tool is lost until you add it to state with the matching `manage_state` `update_*` action.
3. **Save after every change** — Call `/finplan:save-state` immediately after each state mutation, and whenever the user gives new financial information. Don't batch saves.

`update_*` actions normally return a compact delta rather than the full document (the full document comes back with `return_full_state=true`, on a migrated input, or when `update_goal` auto-creates a provisional account); `/finplan:save-state` handles either shape. The full create → integrate → apply delta → save sequence, and the list of events that require a save, are in [state.md](packages/state.md#state-persistence-rules).

## Recommended workflows

**Choosing a projection tool**:

- `project_plan` projects a household. It takes the whole state (`state_json` or a live `state_ref`), projects each account on its own allocation, takes income, expenses and each year's income tax into account, and returns one after-tax outcome. Use it for any question about the user's plan, or about the Larsons, the fictional sample household: "can we retire at 62", "how does our plan look". To project the Larsons, load their state with `/finplan:demo` and pass that file's contents as `state_json`. `get_sample_profile` returns only file URLs, not a `state_ref`.
- `run_projection` projects one balance. You supply the return and volatility, plus any contributions or withdrawals. It knows nothing about accounts, income, expenses or tax. Use it for a standalone "what does $X grow to" question. Get the return and volatility for an allocation from `calculate_portfolio_characteristics`, whose `expected_annual_return` and `annual_volatility` are `run_projection`'s inputs of the same name. `run_projections` runs several in one call.
- `compare_scenarios` compares the plan against what-if variants, projecting each one as a whole plan on the same grid. Use it rather than calling `project_plan` twice and diffing the results yourself. See [scenarios.md](packages/scenarios.md).

**Which tool feeds which**:

- **Mortgage schedule**: `generate_mortgage_amortization_schedule` requires `monthly_payment_cents`. Get it from `calculate_mortgage_monthly_payment` with the same principal, rate and term first, rather than computing the payment yourself.
- **Employer match**: `create_employer_match` builds and validates a match, and reports `is_safe_harbor` and `max_match_pct`. Its `employer_match` object is accepted unchanged as `employer_match_json` by `create_account`, `calculate_401k_employer_match`, `calculate_401k_vested_amount` and `plan_401k_deferral`. Writing `employer_match_json` inline is equivalent. Use `create_employer_match` when you want the formula checked before it goes on an account.
- **Portfolio assumptions**: no tool accepts `create_portfolio_assumptions` output. It shows the per-asset-class returns and volatilities a preset implies, with any overrides applied. To use those numbers, pass the preset name (`assumptions_preset` on `project_plan` and `compare_scenarios`, `assumption_preset` on `calculate_portfolio_characteristics` and `build_snapshot`), or pass the same overrides to `calculate_portfolio_characteristics` (all asset classes) or `build_snapshot` (stocks, bonds and cash only).

**New user setup**: Run `/finplan:setup` for a guided interview that creates the profile, adds accounts, and sets up goals.

**Full planning session**:

1. `/finplan:read-state` to load existing state (or skip if starting fresh)
2. `manage_state(action="create")` → `/finplan:save-state`
3. For each account: `create_account` → `manage_state(action="update_account")` → `/finplan:save-state`
4. For each goal: `create_goal` → `manage_state(action="update_goal")` → `/finplan:save-state`
5. `project_plan` with the saved state to project the household
6. To chart one balance's percentile fan, `generate_projection_fan_chart`. It takes return inputs, as `run_projection` does, not a `project_plan` result

**Periodic review**: Run `/finplan:checkup` to review the plan for life changes, update values, and identify new goals.

**Quick updates**: Use `/finplan:profile`, `/finplan:accounts`, or `/finplan:goals` to view or update individual sections.

**Social Security analysis**:

1. `estimate_social_security_pia_from_earnings_record` to get a PIA from an SSA earnings record — the only tool that can express a stop-work year. `calculate_social_security_pia_from_aime` if the caller already has an AIME; `estimate_social_security_pia_from_salary` only as a flat-career fallback when no earnings record is available.
2. `compare_social_security_claiming_ages` for full claiming-age analysis (benefits, breakevens, life-expectancy sensitivity, household figures) in one call
3. Single-purpose tools (`estimate_social_security_benefits_all_ages`, `estimate_social_security_breakeven_age`, `calculate_social_security_lifetime_benefits`) for month-precision ages or auditing individual figures
