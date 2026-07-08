---
description: Render your base plan vs your saved scenarios as a fully offline, self-contained HTML comparison page — and list or remove scenarios
allowed-tools:
  - Bash(jq *)
  - Bash(curl *)
  - Bash(open *)
  - Bash(python3 *)
  - Bash(rm *)
  - Bash(ls *)
  - Glob
  - Read
  - Write
argument-hint: "[--list] [--remove <slug>]  (no args = render the comparison page)"
---

# /finplan:compare-scenarios — view, compare, and manage your scenarios

Render your **base plan plus every scenario you've saved** as a single, fully
**offline** HTML comparison page (side-by-side fan charts, outcome delta chips, per-goal
success probabilities), and **manage** the scenario set (list, remove). This is the
**comparison level** of the scenario view: base vs each scenario, on one shared grid.

Scenarios are the `scenarios/<slug>.json` files that `/finplan:what-if` writes next to
your state file. This command **reads and manages** that set — it does not create
scenarios. To add one, use `/finplan:what-if "<a plain-English what-if>"`.

Arguments (`$ARGUMENTS`):

- _(none)_ — render/refresh the comparison page for the current `scenarios/` set.
- `--list` — list the saved scenarios (slug, name, description, when saved) and stop.
- `--remove <slug>` — delete `scenarios/<slug>.json` after showing what it is, then stop.

All money is in **integer cents** (`$500.00` = `50000`); rates are decimals (`0.07` = 7%).
All projection math is done server-side by the MCP tools — never do the comparative
arithmetic yourself.

## Step 1: Find the state file and the scenarios directory

1. Glob for `*finplan_state.json` in the working directory (prefer a
   `*_finplan_state.json`; fall back to `finplan_state.json`). If several match, use the
   **newest by mtime** and say which one you picked. If none exists, say so and suggest
   `/finplan:setup` or `/finplan:read-state`, then stop.
2. The scenario set lives in `scenarios/` **next to that state file**. If the directory
   is missing or empty, there is nothing to compare — tell the user to create one with
   `/finplan:what-if "<what-if>"` and stop (for `--list`, just report "no scenarios yet").

## Step 2: Management modes (handle these first, then stop)

**`--list`** — list every `scenarios/*.json`, oldest first by mtime. For each, read the
small file and show: `<slug>`, `name`, the one-line `description`, and the file's saved
date. Do not project anything. Example line:
`retire-at-62 — "Retire at 62": does retiring early still fund college? (saved Jul 8)`.

**`--remove <slug>`** — resolve `scenarios/<slug>.json`. If it doesn't exist, list the
available slugs and stop. Otherwise **read it first and echo what you're about to delete**
(the `name` + `description`), then `rm scenarios/<slug>.json` and confirm. Removal is the
DIY analogue of deleting a snapshot — the set shrinks by one column on the next render.
Do not re-render automatically; tell the user to run `/finplan:compare-scenarios` to
refresh the page.

If neither flag is present, fall through to the render path below.

## Step 3: Pin the base and select the scenario columns

1. Load the state JSON **once** with the `Read` tool — that single read is what you inline
   as `state_json` in Step 4. From it, pull only the header facts you actually display
   (person name(s), age(s), filing status, current net worth). Do **not** `cat`/echo the
   full document to stdout, and do **not** stage it to an intermediate file — both just
   pass the whole state through context a second time for no benefit.
2. Pin the base: the canonical `state_hash` is **derived by the server from the state you
   pass inline** — there is no separate "save" step. Pass the full document as `state_json`
   to the scenario tools; `state_json` is authoritative and the server canonicalizes it,
   echoing the resolved hash back as `inputs.base_state_hash`. If you already know that hash
   (e.g. from an earlier call this session), set `base` to `{"state_hash": "<that hash>"}` to
   pin it; otherwise pass `{"state_hash": "sha256:pending"}` and let the server resolve from
   `state_json`. Every scenario is compared against this base so the columns are
   apples-to-apples.
3. Collect `scenarios/*.json`, **oldest first by file mtime**. This command shows the base
   plus up to **4 scenario columns** (5 total incl. base) — shared-y fan charts get
   unreadable past that. If there are more than 4, keep the **4 newest** and **announce
   which slugs were dropped** in your chat reply.

If the MCP server is unreachable or unauthenticated, say so and stop (offer
`/finplan:diagnose` / `/finplan:login`). This command is MCP-first with no repo fallback.

## Step 4: Project the base and every scenario in one call

Call `compare_scenarios` **once** with the shared `base` (`{"state_hash": …}` plus
`state_ref` if you have one), the state inline (`state_json`), and the list of scenario
documents (read each selected `scenarios/*.json`). Use a consistent
`time_horizon_months` (default 360) so every column lands on one grid. The response gives
you, inline:

- per-scenario **input diff** (what each changes vs base),
- **outcome diff** — household final-balance percentiles and **deltas vs base**,
- **goal deltas** — per-goal success-probability changes vs base (censoring-aware: a
  censored band reports a bound, not a point estimate).

Use the inline `summary` for the cards and delta chips. The full per-scenario percentile
**timelines** live in the data file only — **never read `urls.data` into context**. Its
structure is stable, so you can write the chart JS against these paths directly without a
schema round-trip:

- `timelines.<base|scenario_id>.household_after_tax_percentiles.{10,25,50,75,90}` — an
  array of `{month, total_value}` points per percentile (the fan-chart series).

Reading `urls.schema` is a **fallback** — only download it if these paths don't resolve
(e.g. a field was renamed) or you need to confirm the value unit (dollars vs cents) for a
field.

**Basis consistency.** The `summary` outcome figures and the after-tax timeline can be on
different bases (e.g. the summary's `*_final_balance_cents` p50 need not equal the
`household_after_tax_percentiles.50` endpoint at the same horizon). Pick **one** basis for
the whole page — prefer the after-tax timeline for the headline wealth number so the stat
tile and the fan chart agree — and label the tiles with their basis ("after-tax") so a
reader is never comparing two different numbers on one page.

Surface any warnings `compare_scenarios` returns (base drift, dangling override targets,
no-ops, dropped goals) in your chat reply — a scenario is never silently uncomparable. One
exception: a `base_drift` warning that fires only because you passed the `sha256:pending`
placeholder (with `state_json` supplied and authoritative) is expected plumbing, not a real
mismatch — don't surface it. Surface `base_drift` only when a **real, previously-known**
base hash no longer matches the state.

## Step 5: Render the fully offline comparison page

Write `scenarios/scenario_comparison.html` — a single self-contained file that makes **no
external requests**. Build it from the chart conventions in
[charts.md](../skills/finplan/packages/charts.md) — the **data-handling rules**, the
**placeholder/inject** workflow, **[Fully offline pages (vendored Chart.js)](../skills/finplan/packages/charts.md#fully-offline-pages-vendored-chartjs)**,
and the fixed hues / band opacities / `afterDraw` marker pattern. **charts.md is the single
reference to read** — the exact hues you need are also listed below, so you don't need to
open the `dataviz` skill's palette file. Treat `dataviz` only as the **light + dark
validation standard** the finished palette must pass, not a from-scratch design read.

> **This is a local file on the user's disk, not a claude.ai Artifact.** Produce it with
> the `Write` tool and open it with `open` — do **not** use the Artifact tool or the
> `artifact-design` flow. An Artifact is hosted remotely and would break the offline,
> file-next-to-your-state contract this command exists to provide. `charts.md` is the
> design reference to pull in here.

> **Offline requirement (this is the point of this command).** Do **not** use the Chart.js
> CDN `<script src>`. Put an empty `<script>__CHARTJS__</script>` in the `<head>` and
> inject the vendored bundle at `${CLAUDE_PLUGIN_ROOT}/assets/chart.umd.min.js` on the same
> pass as the data files (Step 6). The finished page must render with the network off.

### Page structure

1. **Header** — household name(s) + age(s), an "as of" date, current net worth, and a line
   naming the scenarios being compared.
2. **Comparison grid** — one column per plan, **base first**, then each scenario in the
   Step 3 order. Each column:
   - Scenario `name` as the title, its one-line `description` underneath (base column
     titled "Your plan (base)").
   - Stat tiles: median (p50) after-tax wealth at the horizon; p10 ("if markets
     disappoint"); each goal's success probability. Every **non-base** column shows a
     **delta chip vs base** (e.g. `−$412k`, `−9 pts`) — always with **sign + label** and a
     status color (good / caution / serious) so meaning never relies on color alone.
     **Per-goal tiles:** drive these from `goal_deltas`. When a scenario returns
     `goal_deltas: []` (some override kinds — e.g. a bare `retirement_age` change — don't
     produce per-goal deltas today), **omit** the per-goal tiles for that column and show a
     one-line "no per-goal change reported" note instead of rendering empty/zeroed tiles.
   - Fan chart of after-tax household wealth, read from `timelines.<base|scenario_id>` in
     the single injected data file: p10–p90 band at low opacity, p25–p75 above it, a solid
     p50 line. **One fixed hue per column, in column order** — base `#3b82f6`, then the four
     scenario slots `#f59e0b`, `#10b981`, `#8b5cf6`, `#ec4899` (one per possible column up to
     the 4-scenario cap) — never re-colored as columns change. Share one y-axis max across
     all columns so the heights compare directly. X-axis in ages; mark the retirement age
     with a dashed vertical line (a small inline `afterDraw` plugin, per charts.md — not a
     vendored annotation plugin).
3. **Footer** — assumptions line (horizon, inflation, method) and a generation timestamp.

### Colors, themes, accessibility

- Use the fixed column hues above (they match `/finplan:what-if` so a scenario keeps its
  color across both pages). Follow the `dataviz` skill's validated **light + dark** palettes
  via `prefers-color-scheme`; both themes must pass the dataviz validator.
- Axis labels ≥ 12px, tooltips on hover, delta chips carry sign + label + status color.

## Step 6: Inject data + Chart.js, then open

`compare_scenarios` returns a **single** `urls.data` file containing every column's
timelines nested under `timelines.<base|scenario_id>` — not one file per scenario. Download
that **one** file to disk (handle `file://` paths directly; `curl` https URLs) into a temp
dir you create first (`mkdir -p /tmp/finplan`), write the HTML with a single `__DATA__`
token plus the `__CHARTJS__` token, then replace both in **one** `python3` pass so nothing
large enters your context. In the page's render loop, index that injected object by column
id (`DATA.timelines[columnId]`) to draw each column.

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
" scenarios/scenario_comparison.html \
  "__CHARTJS__"  "$CLAUDE_PLUGIN_ROOT/assets/chart.umd.min.js" \
  "__DATA__"     "/tmp/finplan/compare_data.json"
```

Open the page with `open scenarios/scenario_comparison.html` on the first render for this
working directory; on reruns just overwrite the file (mention it refreshed).

## Step 7: Report

Reply in chat with a compact verdict only — the columns compared, the headline deltas, any
dropped columns or warnings, e.g.:
`Compared base + 3 scenarios. Retire at 62: median $2.1M → $1.7M (−19%), college 84% → 71%.
Page: scenarios/scenario_comparison.html (offline). Dropped oldest: save-more-500 (cap 4).`

## Notes

- All monetary values from the state file and tools are in **cents** — divide by 100 for
  display.
- This command **reads/lists/removes**; it never writes scenario files. Adding a scenario
  is `/finplan:what-if`'s job — the two meet at the `scenarios/<slug>.json` contract.
- The page is deliberately **offline** (vendored Chart.js) — that is the difference from
  `/finplan:what-if`'s CDN-based comparison page, which this page supersedes as the
  dedicated management surface.
