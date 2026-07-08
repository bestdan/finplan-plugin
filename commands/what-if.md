---
description: Turn a natural-language what-if into a typed scenario, project it against your plan, and refresh a side-by-side comparison page
allowed-tools:
  - Bash(jq *)
  - Bash(curl *)
  - Bash(open *)
  - Bash(python3 *)
  - Glob
  - Read
  - Write
  - Edit
argument-hint: <natural-language what-if>  (e.g. "retire at 62", "save $500 more a month", "what if returns are lower")
---

# /finplan:what-if — build a scenario and compare it to your plan

Turn a plain-English what-if ("retire at 62", "put $500 more a month into the
401(k)", "what if the market drops 20%") into a **typed scenario** against your own
plan, project it, and refresh a side-by-side comparison page. The value this command
adds over calling the MCP directly is the **natural-language → typed-overrides**
translation — you describe the change in words, it produces the validated delta and
the projection.

Arguments: `$ARGUMENTS` — the what-if in natural language. Everything runs against
**your own state file** (the `*_finplan_state.json` convention the other commands
use); there is no external scaffolding to set up.

All money is in **integer cents** (e.g. `$500.00` = `50000`); rates are decimals
(`0.07` = 7%). All projection math is done server-side by the MCP tools — never do
the comparative arithmetic yourself.

## Step 1: Load your plan and pin the base

1. Find the state file with Glob for `*finplan_state.json` in the working directory
   (prefer a `*_finplan_state.json`; fall back to `finplan_state.json`). If none
   exists, say so and suggest `/finplan:setup` or `/finplan:read-state` — then stop.
2. Read it. Pull the header facts for the page (person name(s), age(s), filing
   status, current net worth) — you do not need to hold the whole document in prose,
   but you do need the full JSON to hand to the scenario tools.
3. Pin the base: the canonical `state_hash` is **derived by the server from the state you
   pass inline** — there is no separate "save" step. Keep the full state JSON around and
   pass it as `state_json` to the scenario tools; `state_json` is authoritative and the
   server canonicalizes it, echoing the resolved hash back (as `inputs.base_state_hash`
   from `compare_scenarios`, or in a `base_drift` warning from `create_scenario`). If you
   already know that hash (e.g. from an earlier call this session), set `base` to
   `{"state_hash": "<that hash>"}` to pin it; otherwise pass `{"state_hash": "sha256:pending"}`
   and let the server resolve from `state_json`. Every scenario is authored against this
   base so comparisons are apples-to-apples.

If the MCP server is unreachable or unauthenticated, say so and stop (offer
`/finplan:diagnose` / `/finplan:login`). This command is MCP-first and has no
repo-internal fallback.

## Step 2: Translate the ask into typed overrides

This is the actual work of the command. Map `$ARGUMENTS` onto the scenario override
vocabulary (amounts in cents), each override tagged by `kind`:

- `retirement_age` — "retire at 62" → `{"kind": "retirement_age", "age": 62}`
- `monthly_contribution` — "save $500 more a month" (per-account or household)
- `account_balance` — "assume the house sells for $800k"
- `return_assumption` — "what if returns are lower" (a lower expected return)
- `inflation` — "if inflation runs at 4%"
- `tax_rate` — `marginal_ordinary_rate` and/or `ltcg_rate`
- `income_change` / `expense_change` — a raise, a new expense, a dropped one
- `goal_target` — move a goal's target amount or date

Pick the **smallest** set of overrides that expresses the ask. If the ask does not
map onto any override kind, say so in one line and suggest the nearest expressible
scenario — **do not invent schema**. If it's ambiguous (which account? whose
retirement age?), ask one short clarifying question or state the assumption you made.

## Step 3: Create and store the scenario file

1. Call `create_scenario` with the BaseRef (`{"state_hash": …}`, plus `state_ref` if
   you have one), a short human `name` (the column title, e.g. "Retire at 62"), a
   one-line `description` of the question it explores, the `overrides`, and the state
   inline via `state_json`. Heed any warnings it returns (dangling target, no-op).
2. Write the scenario document from the response's `scenario` key (not the whole
   response) to a **`scenarios/` directory next to your state file** —
   `scenarios/<slug>.json`, where `<slug>` is a short kebab-case name derived from the
   scenario name (e.g. `retire-at-62.json`). Create `scenarios/` if it doesn't exist.
   This is the DIY analogue of `snapshots/`: your scenarios accumulate there and are
   portable JSON you own.

## Step 4: Project the base and every scenario

**Accumulation convention:** the comparison page shows your base plan plus one column
per scenario file in `scenarios/`, capped at 4 scenario columns. When there are more
than 4, **select the 4 most-recently-modified** files (by mtime) and say which were
dropped; then **display those columns oldest → newest** so the base sits leftmost and
the newest what-if is rightmost. A rerun rebuilds every column, so what-ifs accumulate
naturally across a session.

Call `compare_scenarios` **once** with the shared `base`, the state inline
(`state_json`), and the list of scenario documents (read each `scenarios/*.json`).
Use a consistent `time_horizon_months` (default 360) so every column lands on one
grid. The response gives you, inline:

- per-scenario **input diff** (what each changes vs base),
- **outcome diff** — household final-balance percentiles and deltas vs base,
- **goal deltas** — per-goal success-probability changes vs base.

Use the inline `summary` for the cards and delta chips. The full per-scenario
percentile **timelines** live in the data file only — never read `urls.data` into
context. Read `urls.schema` (small) to confirm the field names/paths for the
timelines before you write the chart JS.

Surface any warnings compare_scenarios returns (base drift, dropped goals) in your
chat reply — a scenario is never silently uncomparable. One exception: a `base_drift`
warning that fires only because you passed the `sha256:pending` placeholder (with
`state_json` supplied and authoritative) is expected plumbing, not a real mismatch —
don't surface it. Surface `base_drift` only when a real, previously-known base hash no
longer matches the state.

## Step 5: Render the comparison page

Write `scenarios/what_if_comparison.html` — a single self-contained file. Follow the
chart conventions in [charts.md](../skills/finplan/packages/charts.md) (especially the
**data-handling rules** and the **placeholder/inject** workflow — the timelines must
never pass through your context). Chart.js from the CDN
(`https://cdn.jsdelivr.net/npm/chart.js@4`); everything else inline.

> This is the built-in DIY comparison view. The dedicated scenario-management surface —
> `/finplan:compare-scenarios` (view/compare/manage all your scenarios, fully offline) —
> is a separate command; point the user there when they want to manage or re-render the
> whole set. `/finplan:what-if` renders its own comparison page so it works standalone.
>
> **This is a local file, not a claude.ai Artifact.** Produce it with `Write` and open it
> with `open` — do **not** use the Artifact tool or the `artifact-design` flow, which would
> host it remotely instead of writing it next to the user's state.

Page structure:

1. **Header** — household name(s) + age(s), "as of" date, current net worth, and the
   what-if you just asked.
2. **Comparison grid** — one column per plan, **base first**. Each column:
   - Scenario `name` as the title, its one-line description underneath.
   - Stat tiles: median (p50) after-tax wealth at the horizon; p10 ("if markets
     disappoint"); each goal's success probability. Every non-base column shows a
     **delta chip vs base** (e.g. `−$412k`, `−9 pts`) — always with sign + label, and
     a status color (good / caution / serious) so it never relies on color alone.
   - Fan chart of after-tax household wealth: p10–p90 band at low opacity, p25–p75
     above it, a solid p50 line. **One fixed hue per column in column order** — base
     `#3b82f6`, then the four scenario slots `#f59e0b`, `#10b981`, `#8b5cf6`, `#ec4899`
     (one per possible column up to the 4-scenario cap) — never re-colored as columns
     are added. Share one y-axis max across all columns so the heights are comparable.
     X-axis in ages; mark the retirement age with a dashed vertical line.
3. **Footer** — assumptions line (horizon, inflation, method) and a generation
   timestamp.

`compare_scenarios` returns a **single** data file holding every column's timelines
keyed by `scenario_id` (the base included) — so inject it **once**: write one
`__DATA_COMPARISON__` token, replace it with the on-disk JSON via the `python3`
one-liner (see charts.md), then index each column's timeline off that one object by
`scenario_id`/slug in the chart JS. Do not emit a token per scenario — that would
copy the whole dataset into the page N times. Keep it readable: axis labels ≥ 12px,
tooltips on hover, both light and dark themes via `prefers-color-scheme`, both
validated.

## Step 6: Open and report

Open the page with `open scenarios/what_if_comparison.html` on the first render for
this working directory; on reruns just overwrite the file (mention it refreshed).

Reply in chat with a compact verdict only, e.g.:
`Retire at 62: median $2.1M → $1.7M (−19%), college goal 84% → 71%. Saved
scenarios/retire-at-62.json; comparison page updated.`
