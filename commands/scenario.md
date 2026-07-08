---
description: Drill into one saved scenario — an offline, self-contained page of its overrides, projection detail, and goal outcomes, plus on-demand ad-hoc analyses nested under it
allowed-tools:
  - Bash(jq *)
  - Bash(curl *)
  - Bash(open *)
  - Bash(python3 *)
  - Bash(mkdir *)
  - Bash(ls *)
  - Glob
  - Read
  - Write
argument-hint: "<slug> [--analysis <a plain-English ad-hoc question>]"
---

# /finplan:scenario — drill into one scenario

Focus on **a single saved scenario** and interrogate it. This is the
**single-scenario level** of the scenario view — the drill-down _below_
`/finplan:compare-scenarios`, which shows every scenario side-by-side as peers. Here the
whole page is scoped to one scenario: its overrides, its projection detail, its goal
outcomes — and any **ad-hoc analyses** you attach, which live _inside_ this scenario as
its children (never promoted to peer level with the other scenarios).

The scenario is one of the `scenarios/<slug>.json` files that `/finplan:what-if` writes
next to your state file. See the three-level hierarchy in
[scenarios.md](../skills/finplan/packages/scenarios.md#scenario-view-hierarchy-html-pages):
**comparison (all scenarios) → this single-scenario page → ad-hoc visuals within it.**

Arguments (`$ARGUMENTS`):

- `<slug>` — render/refresh the single-scenario page for `scenarios/<slug>.json`.
- `<slug> --analysis "<question>"` — run an on-demand analysis (e.g. a year-by-year
  tax/college-funding table) and attach it to that scenario's page as a child section.

All money is in **integer cents** (`$500.00` = `50000`); rates are decimals (`0.07` = 7%).
All projection and tax math is done server-side by the MCP tools — never do the arithmetic
yourself.

## Step 1: Resolve the scenario and pin the base

1. Glob for `*finplan_state.json` in the working directory (prefer `*_finplan_state.json`;
   fall back to `finplan_state.json`). If several match, use the **newest by mtime** and say
   which. If none exists, say so, suggest `/finplan:setup` or `/finplan:read-state`, stop.
2. Resolve `scenarios/<slug>.json` next to that state file. If it doesn't exist, list the
   available slugs (like `/finplan:compare-scenarios --list`) and stop. Read it — you need its
   `name`, `description`, `overrides`, and `base`.
3. Read the state JSON (full document for the tools; pull header facts — person name(s),
   age(s), filing status, net worth — for the page).
4. Pin the base the same way the other scenario commands do: the canonical `state_hash` is
   **derived server-side from the state you pass inline** — there is no separate "save" step.
   Pass the full document as `state_json`; it is authoritative and the server echoes the
   resolved hash back (`inputs.base_state_hash`). If you already know the hash this session,
   set `base` to `{"state_hash": "<that hash>"}`; otherwise pass
   `{"state_hash": "sha256:pending"}` and let the server resolve it from `state_json`.

If the MCP server is unreachable or unauthenticated, say so and stop (offer
`/finplan:diagnose` / `/finplan:login`). This command is MCP-first with no repo fallback.

## Step 2: Project this scenario (detail, not comparison)

Call `compare_scenarios` **once** with the shared `base`, the state inline (`state_json`),
and **just this one scenario document**. It returns, inline: the scenario's **input diff**
(its overrides rendered against base), the **outcome diff** (household final-balance
percentiles and deltas vs base), and **goal deltas** (per-goal success-probability changes,
censoring-aware). The base is still projected as the faint reference line — a drill-down is
"this scenario vs where you started," not a bare number.

Use the inline `summary` for the input diff, goal deltas, and delta-chip context. **But the
summary's final-balance figures (`base_final_balance_cents`, `scenarios[].final_balance_cents`)
are _pre-tax_**, and this page's headline tiles are labelled **after-tax** — so do not put the
summary finals in them. Pull the after-tax horizon values (p50, p10) from the **last point of
`household_after_tax_percentiles`** in the downloaded data file (Step 5), read with `jq` on
disk — **never read `urls.data` into context**, and never label a pre-tax number as after-tax.
The per-month timeline lives in the data file only; read `urls.schema` (small) to confirm the
exact field names/paths before writing the chart JS or the `jq` queries.

Suppress the expected `base_drift` warning that fires only from passing the `sha256:pending`
placeholder with an authoritative `state_json`; surface every other warning (dangling
override targets, no-ops, dropped goals) in your chat reply. Note `goal_deltas` may come back
empty for a pure `retirement_age` override — render the empty-state in that case (Step 3.4)
rather than treating it as an error.

For deeper single-scenario drill-downs than the summary exposes (per-account balances,
year-by-year cashflow, tax detail), lean on what the projection already produced: the
`compare_scenarios` **data file** (Step 5) holds the whole-plan, override-applied per-month
timelines (household, after-tax, and per-account series where present) — read the fields you
need from it **on disk with `jq`**. For goal funding use `project_goal_progress` (mind the
funded-balance note in Step 4).

> **Known limitation — do not route around it silently.** `apply_scenario` returns only a
> `state_ref` (+ hash), and today `project_plan` / `run_projection` require `state_json` and do
> **not** accept a `state_ref`. So the `state_ref` is usable for _inspecting_ the resolved
> state, not as a feed into those tools — derive ad-hoc detail from the `compare_scenarios`
> outputs above rather than an `apply_scenario` → `project_plan` chain. Separately,
> projection-time overrides (`return_assumption`, `inflation`, account-scoped
> `monthly_contribution`) have no state slot and only take effect via `compare_scenarios`; a
> state-level number must have them passed explicitly or flag the gap. (Both are tracked as
> engine follow-ups; this command works within them today.)

## Step 3: Render the single-scenario page

Write `scenarios/<slug>/scenario.html` (create the `scenarios/<slug>/` directory first) — a
single, fully **offline** self-contained file that makes **no external requests**. Follow
the `dataviz` skill and the chart conventions in
[charts.md](../skills/finplan/packages/charts.md) — the **data-handling rules**, the
**placeholder/inject** workflow, and **[Fully offline pages (vendored Chart.js)](../skills/finplan/packages/charts.md#fully-offline-pages-vendored-chartjs)**.

> **Offline requirement.** Do **not** use the Chart.js CDN. Put an empty
> `<script>__CHARTJS__</script>` in the `<head>` and inject the vendored bundle at
> `${CLAUDE_PLUGIN_ROOT}/assets/chart.umd.min.js` on the same pass as the data files
> (Step 5). The page must render with the network off.

### Page structure

1. **Header** — the scenario `name` as the title, its `description` underneath, the
   household name(s) + age(s), an "as of" date, and a **back-link to the comparison page**
   (`../scenario_comparison.html`, labelled e.g. "← All scenarios"). Make the lineage
   explicit: this page is one scenario within that comparison.
2. **Overrides** — the typed delta in plain language (what this scenario changes vs base:
   "Retirement age → 62", "Monthly 401(k) contribution +$500", …), read from the input diff.
3. **Projection detail** — a fan chart of this scenario's after-tax household wealth
   (p10–p90 / p25–p75 bands, solid p50), with the **base** drawn as a faint reference line
   so the delta is visible. Use this scenario's **fixed column hue** so it matches its column
   in the comparison page. Determine the hue the same way `/finplan:compare-scenarios` assigns
   columns: list `scenarios/*.json` oldest-first by mtime and keep the 4 newest, then take this
   scenario's index in that kept list and map it to the fixed palette — base `#3b82f6`, then
   `#f59e0b`, `#10b981`, `#8b5cf6` in column order (if this scenario falls outside the newest 4,
   use the next hue and say so). Stat tiles: median (p50) and p10 after-tax wealth
   at the horizon, each with a **delta chip vs base** (sign + label + status color). Milestone
   lines (e.g. retirement age) via a tiny inline `afterDraw` plugin, per charts.md.
4. **Goal outcomes** — per-goal success probability under this scenario, each with its
   **delta vs base** (censoring-aware: show a bound when the band is censored).
5. **Ad-hoc analyses** — a section that renders every ad-hoc attached to this scenario (see
   Step 4). On a plain render with no ad-hocs yet, show a short empty-state line telling the
   user they can add one with `/finplan:scenario <slug> --analysis "<question>"`.
6. **Footer** — assumptions line (horizon, inflation, method) and a generation timestamp.

Light + dark via `prefers-color-scheme`, both validated by the dataviz validator; axis
labels ≥ 12px; tooltips on hover; delta chips carry sign + label + status color.

## Step 4: Ad-hoc analyses (only when `--analysis` is given)

An **ad-hoc** is an on-demand analysis that belongs to _this_ scenario — a child of it, not
a peer scenario. The value you add is the same natural-language translation `/what-if` adds:
turn the `--analysis` question into the right MCP tool calls, then render the result as a
nested section on this scenario's page.

1. **Translate the question into a computation** over this scenario's _own_ projected world —
   the override-applied outputs from Step 2 (the `compare_scenarios` data file for
   balances/timelines, `project_goal_progress` for goal funding); not `apply_scenario`'s
   `state_ref` (see the Step 2 limitation). Pick the tools the question needs — e.g. a
   **year-by-year tax/college table** composes the capital-gains, federal-liability, NIIT, and
   state-tax tools per year with `project_goal_progress` for each 529's funding; a **per-account
   breakdown** reads the per-account series from the data file, or runs `run_projection` per
   account. **Funded balance:** when you call `project_goal_progress`, pass the goal's _funded_
   balance — the sum of accounts linked by `goal_id` — **not** the goal's own
   `current_balance_cents`, which is often `0` (passing it projects the goal from $0). If the ask
   doesn't map onto available tools, say so in one line and suggest the nearest expressible
   analysis — do not fabricate numbers.
2. **Persist the ad-hoc** so re-renders replay it: write a small spec+data file to
   `scenarios/<slug>/adhoc/<analysis-slug>.json` — `{title, question, kind, columns, rows}`
   (or a compact data shape for a chart). This is what makes the ad-hoc a durable **child**
   of the scenario: it lives under the scenario's own directory and is never written to
   `scenarios/` at peer level. Ad-hocs accumulate; a re-render shows all of them.
3. **Re-render** `scenarios/<slug>/scenario.html` (Steps 3 + 5), reading **every**
   `scenarios/<slug>/adhoc/*.json` (oldest first by mtime) into the ad-hoc section — each as
   its own titled sub-card (a table and/or a small chart), clearly nested under the scenario
   with the question it answers as the sub-heading. Large per-year datasets follow the same
   placeholder/inject rule; small tables (a handful of rows, like the year-by-year example)
   may be written inline as they are already summary-sized.

**Motivating demo** (the acceptance example): within a "Stage RSU Sale Over 4 Years"
scenario, `--analysis "year-by-year realized LTCG, estimated tax (fed + NIIT + CA), and
529/college funding"` → a 4-row table (one row per year) with columns for realized LTCG,
federal LTCG tax, NIIT, CA tax, total tax, and 529 contribution/funding — rendered as a
sub-card in the ad-hoc section of that scenario's page, not as a new scenario column.

## Step 5: Inject data + Chart.js, then open

Download this scenario's (and the base's) timeline from the `compare_scenarios` data file to
disk (handle `file://` paths directly; `curl` https URLs), write the HTML with
`__DATA_<SLUG>__` / `__DATA_BASE__` tokens plus the `__CHARTJS__` token (and any per-ad-hoc
data tokens), then replace every token in **one** `python3` pass so nothing large enters your
context:

> **Keep the page re-editable.** Ad-hoc accumulation means this file gets rewritten repeatedly,
> so emit **line-broken** markup (real newlines, not one giant line) and place the big injected
> blobs — `__CHARTJS__` and every `__DATA_*__` token — in a **single `<script>` block at the
> tail**, just before `</body>`. The vendored Chart.js + data is ~350 KB; if it lands mid-file
> on one line, the page can't be re-read (`Read` exceeds token limits even with offset/limit) or
> `Edit`ed, forcing every ad-hoc re-render through raw string replacement. Small human-readable
> structure up top + one heavy blob at the bottom keeps re-renders and inspection cheap.

```bash
python3 -c "
import sys
html_path = sys.argv[1]
with open(html_path) as f:
    html = f.read()
replacements = dict(zip(sys.argv[2::2], sys.argv[3::2]))
for token, path in replacements.items():
    path = path.replace('file://', '') if path.startswith('file://') else path
    with open(path) as f:
        html = html.replace(token, f.read())
with open(html_path, 'w') as f:
    f.write(html)
" scenarios/<slug>/scenario.html \
  "__CHARTJS__"     "$CLAUDE_PLUGIN_ROOT/assets/chart.umd.min.js" \
  "__DATA_BASE__"   "/tmp/finplan/base_data.json" \
  "__DATA_<SLUG>__" "/tmp/finplan/<slug>_data.json"
```

Open the page with `open scenarios/<slug>/scenario.html` on the first render for this
scenario; on reruns (including after adding an ad-hoc) just overwrite the file (mention it
refreshed).

## Step 6: Report

Reply in chat with a compact verdict only — the scenario, its headline delta vs base, and
what changed on the page, e.g.:
`Retire at 62 (vs base): median $2.1M → $1.7M (−19%), college 84% → 71%. Added ad-hoc
"year-by-year RSU tax". Page: scenarios/retire-at-62/scenario.html (offline).`

## Notes

- **Hierarchy:** comparison (`scenarios/scenario_comparison.html`, all scenarios) → this
  single-scenario page (`scenarios/<slug>/scenario.html`) → ad-hoc visuals
  (`scenarios/<slug>/adhoc/*.json`). Ad-hocs are **children** of their scenario — one scenario
  owns them; they never appear as a peer scenario in the comparison view.
- This command **reads** the scenario and **writes only under `scenarios/<slug>/`** (its page
  and its ad-hocs). It never creates or edits `scenarios/<slug>.json` — that's
  `/finplan:what-if`'s job — and never touches the peer-level comparison page.
- All monetary values from the state file and tools are in **cents** — divide by 100 for
  display.
