# Scenario Tools

Create, apply, and compare plan scenarios — "what if" deltas (retire at 60, save $500 more, lower returns) against a base plan. Numbers are always re-derived server-side by projecting the whole plan per scenario; never do the comparative arithmetic yourself.

**Terminology:**

- **Scenario**: a named, ordered list of typed overrides (a delta) applied against a base `UserState`. It stores only inputs; outcomes are always re-derived.
- **Override**: one typed change, tagged by `kind`: `retirement_age`, `return_assumption`, `inflation`, `tax_rate` (at least one of `marginal_ordinary_rate` / `ltcg_rate`), `monthly_contribution`, `account_balance`, `income_change`, `expense_change`, `goal_target`. Amounts are in cents. E.g. `{"kind": "retirement_age", "age": 60}`.
- **BaseRef**: identifies the base plan: `{"state_hash": "sha256:…"}` (required — the hash `manage_state` returns) plus an optional `"state_ref": "st_…"` in-session accelerator. Supplying `state_json` inline always works and takes precedence.
- Distinct from `compare_return_assumptions`, which varies return assumptions on a single balance — these tools compare whole _plans_.

## Tools

### create_scenario

Create a plan scenario: a named, validated delta of typed overrides against a base plan. Returns a small, portable scenario document the client owns — store it and pass it to `compare_scenarios` (or `apply_scenario`). Overrides are validated against the base: dangling target ids and no-ops surface as warnings, never silent drops.

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

The headline tool: compare plan scenarios against a base plan in one server-side operation. Each scenario's whole plan is projected (per-account allocations, household surplus split, after-tax treatment) and diffed against the base by `scenario_id`. Returns the input diff (what each scenario changes) and the outcome diff (household final-balance percentiles and deltas vs base) inline, with full per-scenario percentile timelines in the data file. Goal-outcome deltas are not part of this comparison.

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

1. `manage_state` (or `save_user_state`) → note the returned `state_hash` (and `state_ref` if uploaded).
2. `create_scenario` with the BaseRef and overrides → store the returned scenario document client-side.
3. `compare_scenarios` with the same BaseRef and the scenario document(s) → present the inline summary; pull timelines from the data file for charts.
4. Optionally `apply_scenario` to get a `state_ref` for the hypothetical state, usable with other state-driven tools.
