# Scenario Tools

Create, apply, and compare plan scenarios — "what if" deltas (retire at 60, save $500 more, lower returns) against a base plan. Numbers are always re-derived server-side by projecting the whole plan per scenario; never do the comparative arithmetic yourself.

**Terminology:**

- **Scenario**: a named, ordered list of typed overrides (a delta) applied against a base `UserState`. It stores only inputs; outcomes are always re-derived.
- **Override**: one typed change, tagged by `kind`: `retirement_age`, `return_assumption`, `inflation`, `tax_rate` (at least one of `marginal_ordinary_rate` / `ltcg_rate`), `monthly_contribution`, `account_balance`, `income_change`, `expense_change`, `goal_target`. Amounts are in cents. E.g. `{"kind": "retirement_age", "age": 60}`.
- **BaseRef**: identifies the base plan: `{"state_hash": "sha256:…"}` plus an optional `"state_ref": "st_…"` in-session accelerator. The canonical `state_hash` is derived server-side from the state you pass inline as `state_json` (echoed back as `base_state_hash`) — there is no separate "save" step. Supplying `state_json` inline always works and takes precedence; if you don't yet know the hash, pass `{"state_hash": "sha256:pending"}` and let the server resolve it from `state_json`.
- **Authority boundaries**: the `UserState` owns current facts (mutated only via `manage_state`); a Snapshot is an immutable point-in-time record; a Scenario owns hypothetical intent only. Computed outcomes live in none of them — always re-derived.
- Distinct from `compare_return_assumptions`, which varies return assumptions on a single balance — these tools compare whole _plans_.

## Tools

### create_scenario

Create a plan scenario: a named, validated delta of typed overrides against a base plan. The response nests the scenario document under its `scenario` key — small, portable JSON the client owns. Store that document (not the whole response) and pass it to `compare_scenarios` (or `apply_scenario`). Overrides are validated against the base: dangling target ids and no-ops surface as warnings, never silent drops.

| Parameter     | Type       | Description                                                                                                    |
| ------------- | ---------- | -------------------------------------------------------------------------------------------------------------- |
| `base`        | object     | BaseRef the scenario is authored against: `{"state_hash": …, "state_ref"?: …}`.                                |
| `name`        | string     | Human label, e.g. `"Retire at 60"`.                                                                            |
| `overrides`   | list[dict] | Ordered, typed overrides (the delta), each tagged by `kind`. Amounts in cents.                                 |
| `description` | string     | What question this scenario explores. Defaults to a generated summary of the overrides.                        |
| `state_json`  | object     | The base UserState document inline. Optional when `base.state_ref` is still live; takes precedence when given. |

### apply_scenario

Resolve a scenario's state-shaped overrides against the base and return a `state_ref` to the resolved (hypothetical) UserState for inspection or handing to other tools. The resolved state is ephemeral compute scratch (60-minute TTL) — it never becomes the base UserState. Projection-time overrides (`return_assumption`, `inflation`, account-scoped `monthly_contribution`) have no state slot and only take effect when the scenario is projected via `compare_scenarios`.

| Parameter    | Type   | Description                                                                                                    |
| ------------ | ------ | -------------------------------------------------------------------------------------------------------------- |
| `base`       | object | BaseRef: `{"state_hash": …, "state_ref"?: …}`.                                                                 |
| `scenario`   | object | The scenario to apply: a `create_scenario` document, or a minimal `{"name": …, "overrides": […]}` sketch.      |
| `state_json` | object | The base UserState document inline. Optional when `base.state_ref` is still live; takes precedence when given. |

### compare_scenarios

The headline tool: compare plan scenarios against a base plan in one server-side operation. Each scenario's whole plan is projected (per-account allocations, household surplus split, after-tax treatment) and diffed against the base by `scenario_id`. Returns the input diff (what each scenario changes), the outcome diff (household final-balance percentiles and deltas vs base), and per-goal deltas (success-probability changes, `meets_importance` flips) inline, with full per-scenario percentile timelines and goal-delta records in the data file. Goal success probabilities are censored to [0.10, 0.90]: a censored side reports the delta as a bound (`>=`/`<=`), not a point estimate. Goal deltas are a separate lens — goal bands use a blended return and are **not** numerically consistent with the portfolio percentile timelines; cite them side by side, never reconcile them. A goal a scenario's overrides drop out of evaluation surfaces as a per-scenario warning.

Provide **either** `base` + `scenarios` **or** a `scenario_set`, not both.

| Parameter                | Type       | Description                                                                                                                      |
| ------------------------ | ---------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `base`                   | object     | BaseRef shared by the scenarios. Required with `scenarios`; ignored in favor of the set-level base when `scenario_set` is given. |
| `scenarios`              | list[dict] | Scenarios to compare against the base: `create_scenario` documents or minimal `{"name": …, "overrides": […]}` sketches.          |
| `scenario_set`           | object     | A portable `finplan_scenario_set` document (`{"base": BaseRef, "scenarios": […]}`); its set-level base is authoritative.         |
| `state_json`             | object     | The base UserState document inline. Optional when the base's `state_ref` is still live; takes precedence when given.             |
| `time_horizon_months`    | int        | Months to project (default: 360 = 30 years). Shared by the base and every scenario so outcomes land on one comparable grid.      |
| `assumptions_preset`     | string     | Capital-market assumptions the scenarios vary from: `"standard"` (default), `"conservative"`, or `"optimistic"`.                 |
| `inflation`              | float      | Baseline annual inflation rate as a decimal (default: 0.0). An inflation override in a scenario replaces it for that scenario.   |
| `percentiles`            | list[int]  | Percentiles to compute (default: [10, 25, 50, 75, 90]).                                                                          |
| `marginal_ordinary_rate` | float      | Household marginal ordinary income tax rate for after-tax values (default: 0.22).                                                |
| `ltcg_rate`              | float      | Household long-term capital gains tax rate for after-tax values (default: 0.15).                                                 |
| `method`                 | string     | `"closed_form"` (default), `"deterministic"`, `"monte_carlo"`.                                                                   |
| `iterations`             | int        | Monte Carlo iterations (default: 1000, only used for `method="monte_carlo"`).                                                    |
| `seed`                   | int        | Random seed (only used for `method="monte_carlo"`).                                                                              |

**Response**: file URLs + compact inline summary (per-scenario input diff, final-balance percentiles and deltas vs base, warnings). The per-month timelines live in the data file only.

**Warnings**: base drift (scenario authored against a different `state_hash`), dangling override targets (skipped for this run), and no-ops all surface as warnings — a scenario is never silently uncomparable. Global warnings are top-level; per-scenario warnings sit on each entry under `outputs.scenarios[].warnings`.

## Typical workflow

1. Pass the full state inline as `state_json`; the server canonicalizes it and echoes back the resolved `base_state_hash`. Pin `base` to that hash (or pass `{"state_hash": "sha256:pending"}` and let the server resolve from `state_json`) — there is no separate "save" step.
2. `create_scenario` with the BaseRef and overrides → store the scenario document from the response's `scenario` key client-side.
3. `compare_scenarios` with the same BaseRef and the scenario document(s) → present the inline summary; pull timelines from the data file for charts.
4. Optionally `apply_scenario` to get a `state_ref` for the hypothetical state, usable with other state-driven tools.

## Scenario view hierarchy (HTML pages)

The plugin renders scenarios as **offline, self-contained HTML** at three nested levels. Each level is one step more focused than the one above it, and the files live in a matching directory shape next to the user's state file:

| Level               | Scope                                                                                 | Page                                                                        | Command                                   |
| ------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------- |
| **Comparison**      | base vs **all** scenarios, side-by-side as peers                                      | `scenarios/scenario_comparison.html`                                        | `/finplan:compare-scenarios`              |
| **Single scenario** | **one** scenario's overrides, projection detail, goal outcomes                        | `scenarios/<slug>/scenario.html`                                            | `/finplan:scenario <slug>`                |
| **Ad-hoc visual**   | an on-demand analysis **within** one scenario (e.g. a year-by-year tax/college table) | `scenarios/<slug>/adhoc/<analysis>.json` → rendered on that scenario's page | `/finplan:scenario <slug> --analysis "…"` |

```
scenarios/
  scenario_comparison.html      # comparison level — all scenarios
  <slug>.json                   # the scenario record (/finplan:what-if writes this)
  <slug>/
    scenario.html               # single-scenario drill-down page
    adhoc/
      <analysis>.json           # ad-hoc analysis, a child of this scenario
```

**Drill direction:** a scenario column in the comparison page links down to that scenario's `<slug>/scenario.html`; the single-scenario page links back up to `../scenario_comparison.html`. **Ad-hocs are children of their scenario** — they render on `<slug>/scenario.html` and are stored under `scenarios/<slug>/adhoc/`, never promoted to a peer scenario at the comparison level. All three levels use the vendored-Chart.js offline convention and the light+dark dataviz palettes (see [charts.md](charts.md#fully-offline-pages-vendored-chartjs)).
