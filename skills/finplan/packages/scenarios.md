# Scenario Tools

Create, apply, and compare plan scenarios — "what if" deltas (retire at 60, save $500 more, lower returns) against a base plan. Numbers are always re-derived server-side by projecting the whole plan per scenario; never do the comparative arithmetic yourself.

**Terminology:**

- **Scenario**: a named, ordered list of typed overrides (a delta) applied against a base `UserState`. It stores only inputs; outcomes are always re-derived.
- **Override**: one typed change, tagged by `kind`: `retirement_age`, `return_assumption`, `inflation`, `tax_rate` (at least one of `marginal_ordinary_rate` / `ltcg_rate`), `monthly_contribution`, `account_balance`, `income_change`, `expense_change`, `goal_target`. Amounts are in cents. E.g. `{"kind": "retirement_age", "age": 60}`.
- **BaseRef**: identifies the base plan: `{"state_hash": "sha256:…"}` plus an optional `"state_ref": "st_…"` in-session accelerator. The canonical `state_hash` is derived server-side from the state you pass inline as `state_json` (echoed back as `base_state_hash`) — there is no separate "save" step. `create_scenario` returns `base_state_ref`; `compare_scenarios` returns it under `summary.inputs.base_state_ref`. Reuse that handle as `base.state_ref` instead of inlining state. Refs have an approximately 60-minute sliding TTL that refreshes on each use; on `state_ref_expired`, re-send the full `state_json` in that same call. Supplying `state_json` inline always works and takes precedence; if you don't yet know the hash, pass `{"state_hash": "sha256:pending"}` and let the server resolve it from `state_json`.
- **Authority boundaries**: the `UserState` owns current facts (mutated only via `manage_state`); a Snapshot is an immutable point-in-time record; a Scenario owns hypothetical intent only. Computed outcomes live in none of them — always re-derived.
- Distinct from `compare_return_assumptions`, which varies return assumptions on a single balance — these tools compare whole _plans_.

<!-- BEGIN GENERATED: tool-index scenario -->

## Tool index

| Tool                | Description                                                                                                                             | Parameters                                                                                                                                                                                                                   |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apply_scenario`    | Resolve a scenario's overrides against the base plan and return a state_ref to the hypothetical state for inspection.                   | base (BaseRef), scenario, state_json?, return_state_json?                                                                                                                                                                    |
| `compare_scenarios` | Compare plan scenarios against a base plan: project each scenario's whole plan server-side and diff inputs and outcomes.                | scenarios\|scenario_set, base (req. with scenarios), state_json?, time_horizon_months?, assumptions_preset?, inflation?, percentiles?, marginal_ordinary_rate?, ltcg_rate?, method?, iterations?, seed?, compute_income_tax? |
| `create_scenario`   | Create a plan scenario: a named, validated delta of typed overrides (retire earlier, save more, different returns) against a base plan. | base (BaseRef), name, overrides, description?, state_json?                                                                                                                                                                   |

<!-- END GENERATED: tool-index scenario -->

## Tools

### create_scenario

The response nests the scenario document under its `scenario` key — small, portable JSON the client owns — and returns `base_state_ref` for reuse as `base.state_ref` while live. Store the scenario document (not the whole response) and pass it to `compare_scenarios` (or `apply_scenario`). Overrides are validated against the base: dangling target ids and no-ops surface as warnings, never silent drops.

- `base` is `{"state_hash": …, "state_ref"?: …}`.
- `overrides` are ordered, typed, each tagged by `kind`; amounts in cents.
- `description` defaults to a generated summary of the overrides.
- `state_json` is optional when `base.state_ref` is still live; it takes precedence when given.

### apply_scenario

The resolved state is ephemeral compute scratch (60-minute TTL) — it never becomes the base UserState. Projection-time overrides (`return_assumption`, `inflation`, account-scoped `monthly_contribution`) have no state slot and only take effect when the scenario is projected via `compare_scenarios`.

- `scenario` is a `create_scenario` document, or a minimal `{"name": …, "overrides": […]}` sketch.
- `state_json` is optional when `base.state_ref` is still live; it takes precedence when given.
- `return_state_json=True` also returns the resolved hypothetical UserState inline as `state_json`; pass it to `project_plan` / `run_projection` to drive the state-level drill-down off the scenario.

### compare_scenarios

Goal success probabilities are censored to [0.10, 0.90]: a censored side reports the delta as a bound (`>=`/`<=`), not a point estimate. Goal deltas are a separate lens — goal bands use a blended return and are **not** numerically consistent with the portfolio percentile timelines; cite them side by side, never reconcile them. A goal a scenario's overrides drop out of evaluation surfaces as a per-scenario warning.

Provide **either** `base` + `scenarios` **or** a `scenario_set`, not both.

- `base` is required with `scenarios`; it is ignored in favor of the set-level base when `scenario_set` is given.
- `scenarios` are `create_scenario` documents or minimal `{"name": …, "overrides": […]}` sketches.
- `scenario_set` is a portable `finplan_scenario_set` document (`{"base": BaseRef, "scenarios": […]}`); its set-level base is authoritative.
- `state_json` is optional when the base's `state_ref` is still live; it takes precedence when given.
- `time_horizon_months` defaults to 360 (30 years) and is shared by the base and every scenario so outcomes land on one comparable grid.
- `assumptions_preset` defaults to `"standard"`.
- `inflation` is a decimal (default 0.025; 0 gives nominal dollars). An inflation override in a scenario replaces it for that scenario.
- `percentiles` defaults to [10, 25, 50, 75, 90].
- `marginal_ordinary_rate` (default 0.22) and `ltcg_rate` (default 0.15) are household rates for after-tax values.
- `method` defaults to `"closed_form"`. `iterations` (default 1000) and `seed` apply only to `method="monte_carlo"`; `seed` pins the draw, and omitting it uses a fixed default.

The response is file URLs plus a compact inline summary, including `summary.inputs.base_state_ref` for reuse as `base.state_ref` while live. The per-month timelines live in the data file only.

**Warnings**: base drift (scenario authored against a different `state_hash`), dangling override targets (skipped for this run), and no-ops all surface as warnings — a scenario is never silently uncomparable. Global warnings are top-level; per-scenario warnings sit on each entry under `outputs.scenarios[].warnings`.

## Typical workflow

1. Pass the full state inline as `state_json`; the server canonicalizes it and returns the resolved `base_state_hash` plus reusable `base_state_ref`. Pin `base` to that hash (or pass `{"state_hash": "sha256:pending"}` and let the server resolve from `state_json`) — there is no separate "save" step.
2. `create_scenario` with the BaseRef and overrides → store the scenario document from the response's `scenario` key client-side.
3. `compare_scenarios` with the same BaseRef and the scenario document(s) → present the inline summary; pull timelines from the data file for charts.
4. Optionally `apply_scenario` to get a `state_ref` for the hypothetical state, usable with other state-driven tools including `project_plan`.

## HTML pages

The plugin's `/finplan:compare-scenarios` and `/finplan:scenario` commands render these results as offline HTML pages next to the user's state file. The page layout is defined in those commands.
