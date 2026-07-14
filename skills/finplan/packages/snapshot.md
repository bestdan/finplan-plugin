# Snapshot Tools

Build immutable, point-in-time facts records (snapshots) from planning state, and diff two of them. Snapshots are how recurring check-ins capture "what was true on date X" — frozen, versioned, and diffable.

## Tools

### build_snapshot

Build an immutable snapshot from a `finplan_state` document: net worth, category and account-type rollups, allocation analytics, income, and goal funding, with the facts frozen losslessly.

| Parameter           | Type   | Description                                                                                                                                                                                                                                                            |
| ------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `state_json`        | object | A `finplan_state` document (the planning state to capture), passed inline. Provide exactly one of `state_json`, `state_path`, or `state_ref`.                                                                                                                          |
| `state_path`        | string | Path to a `finplan_state` JSON file to capture (e.g. from save-state), loaded in place of `state_json`. Local (stdio) transport only — rejected off stdio; send `state_json` inline there (one-of).                                                                    |
| `state_ref`         | string | Opaque handle to a `finplan_state` document already uploaded to the server (via `POST /state`), resolved without re-sending it inline — the way to build on a hosted server without the document entering context. A ref-fed build reports `migrated: false` (one-of). |
| `as_of`             | string | Logical check-in date these facts represent, ISO format (YYYY-MM-DD). Required to build a snapshot; ignored for `dry_run`.                                                                                                                                             |
| `dry_run`           | bool   | Validate and migrate the state without building a snapshot — a cheap "is this state usable?" check. Returns `{success, valid, migrated, errors, warnings, schema_drift, migrated_state?}` and skips the projection (default: false).                                   |
| `assumption_preset` | string | `"standard"`, `"conservative"`, or `"optimistic"` (default: standard)                                                                                                                                                                                                  |
| `stocks_return`     | float  | Override stock expected return (optional)                                                                                                                                                                                                                              |
| `stocks_volatility` | float  | Override stock volatility (optional)                                                                                                                                                                                                                                   |
| `bonds_return`      | float  | Override bond expected return (optional)                                                                                                                                                                                                                               |
| `bonds_volatility`  | float  | Override bond volatility (optional)                                                                                                                                                                                                                                    |
| `cash_return`       | float  | Override cash expected return (optional)                                                                                                                                                                                                                               |
| `cash_volatility`   | float  | Override cash volatility (optional)                                                                                                                                                                                                                                    |
| `inflation`         | float  | Annual inflation rate (e.g. 0.025 = 2.5%) used to inflate real-terms goal targets to nominal before computing each goal's projected progress. Defaults to the engine's canonical rate (2.5%); pass 0 to disable. Recorded in the snapshot's assumptions stamp.         |

Rejects a document whose `kind` is not `finplan_state`. The generation time is stamped (UTC) in the snapshot's provenance; custom assumptions are labeled `"custom"`. Returns: `snapshot_ref` and `urls` — the full `finplan_snapshot` document stays in the file store and must not be loaded into context — plus the compact `derived` and `provenance` blocks inline. `derived` carries the rollups for the check-in narrative; pass `snapshot_ref` to `diff_snapshots` or the check-in template when the full document is needed.

### diff_snapshots

Compute structured, signed deltas between two snapshots (old → new): money deltas in integer cents, allocation deltas in percentage points. Account types and goals present in only one snapshot are reported as added/removed.

| Parameter           | Type   | Description                                                                                                                                                                                            |
| ------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `old_snapshot_json` | object | The earlier `finplan_snapshot` document, passed inline. Provide exactly one of `old_snapshot_json` or `old_ref`.                                                                                       |
| `new_snapshot_json` | object | The later `finplan_snapshot` document, passed inline. Provide exactly one of `new_snapshot_json` or `new_ref`.                                                                                         |
| `old_ref`           | string | `snapshot_ref` of the earlier snapshot in the server's file store (as returned by `build_snapshot`), resolved in place of `old_snapshot_json` so the full document need not re-enter context (one-of). |
| `new_ref`           | string | `snapshot_ref` of the later snapshot in the server's file store (as returned by `build_snapshot`), resolved in place of `new_snapshot_json` (one-of).                                                  |

Rejects a document whose `kind` is not `finplan_snapshot`. Returns: `diff` with `as_of_old`/`as_of_new` and per-section deltas.

### get_checkin_template

Return the canonical check-in narrative template as plaintext markdown (no parameters). The template is YAML front-matter (`type: checkin`, `as_of`) plus a facts table of `${dotted.path}` markers and reserved `${narrative:*}` sections.

The template is versioned with the snapshot schema, so fetch it fresh rather than caching a copy. Fill it against a `finplan_snapshot`: `${dotted.path}` markers resolve against the snapshot JSON (a `*_cents` leaf renders as a dollar amount), while `${narrative:*}` markers are left untouched for the strategy/narrative layer (or a human) to write. Returns: `template` (markdown string).

### fill_checkin_template

Fill a check-in template's facts markers directly from a `finplan_snapshot`, so consumers never map dotted paths or convert cents → dollars by hand. This is the MCP surface of the internal filler, so its output cannot drift from the snapshot.

| Parameter       | Type   | Description                                                                                             |
| --------------- | ------ | ------------------------------------------------------------------------------------------------------- |
| `snapshot_json` | object | A `finplan_snapshot` document to fill the template from                                                 |
| `template`      | string | Template markdown with `${dotted.path}` markers (optional; defaults to the canonical check-in template) |

Substitutes every resolvable `${dotted.path}` marker (`${derived.*}`, `${provenance.*}`, `${as_of}`, etc.; `*_cents` leaves rendered as dollar amounts) and leaves `${narrative:*}` markers — and any path it cannot resolve — verbatim. Rejects a document whose `kind` is not `finplan_snapshot`. Returns: `filled` (the substituted markdown) and `unresolved` (non-narrative markers that had no matching snapshot value).
