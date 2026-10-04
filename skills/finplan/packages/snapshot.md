# Snapshot Tools

Build immutable, point-in-time facts records (snapshots) from planning state, and diff two of them. Snapshots are how recurring check-ins capture "what was true on date X" — frozen, versioned, and diffable.

<!-- BEGIN GENERATED: tool-index snapshot -->

## Tool index

| Tool                    | Description                                                                                                                                     | Parameters                                                 |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `build_snapshot`        | Build an immutable, versioned point-in-time snapshot from a planning-state document.                                                            | state_json, as_of, assumption_preset?, stocks_return?, ... |
| `diff_snapshots`        | Compute structured, signed deltas between two snapshots (net worth, allocation, goals).                                                         | old_snapshot_json, new_snapshot_json                       |
| `fill_checkin_template` | Fill a check-in template's ${dotted.path} markers from a snapshot (cents rendered as dollars; ${narrative:*} and unresolvable paths preserved). | snapshot_json, template?                                   |
| `get_checkin_template`  | Return the canonical check-in narrative template (markdown with ${dotted.path} markers).                                                        | (no parameters)                                            |

<!-- END GENERATED: tool-index snapshot -->

## Tool notes

### build_snapshot

Provide exactly one of `state_json` or `state_ref` (`state_path` is local transport only and not accepted on the hosted server). A ref-fed build reports `migrated: false`. It rejects a document whose `kind` is not `finplan_state`. The generation time is stamped (UTC) in the snapshot's provenance; custom assumptions are labeled `"custom"`.

- `as_of` (ISO YYYY-MM-DD) is required to build a snapshot, and ignored for `dry_run`.
- `dry_run=true` validates and migrates the state without building a snapshot, and skips the projection: a cheap "is this state usable?" check. It returns `{success, valid, migrated, errors, warnings, schema_drift, migrated_state?}`.
- `assumption_preset` is `"standard"` (default), `"conservative"`, or `"optimistic"`. The `stocks_`, `bonds_` and `cash_` `return` / `volatility` parameters override that preset.
- `inflation` (e.g. 0.025 = 2.5%) inflates real-terms goal targets to nominal before computing each goal's projected progress. It defaults to the engine's canonical rate (2.5%); pass 0 to disable. It is recorded in the snapshot's assumptions stamp.
- The full `finplan_snapshot` document stays in the file store ([don't load it into context](../SKILL.md#data-files-stay-out-of-context)); the compact `derived` and `provenance` blocks come back inline.

### diff_snapshots

Deltas run old → new: money in integer cents, allocation in percentage points. Account types and goals present in only one snapshot are reported as added/removed. Provide exactly one of `old_snapshot_json` or `old_ref`, and exactly one of `new_snapshot_json` or `new_ref`. The refs are `snapshot_ref` values from `build_snapshot`, so the full document need not re-enter context. It rejects a document whose `kind` is not `finplan_snapshot`.

### get_checkin_template

The template is YAML front-matter (`type: checkin`, `as_of`) plus a facts table of `${dotted.path}` markers and reserved `${narrative:*}` sections. It is versioned with the snapshot schema, so fetch it fresh rather than caching a copy. `${dotted.path}` markers resolve against the snapshot JSON (a `*_cents` leaf renders as a dollar amount), while `${narrative:*}` markers are left untouched for the strategy/narrative layer (or a human) to write.

### fill_checkin_template

You never map dotted paths or convert cents to dollars by hand. `template` is optional and defaults to the canonical check-in template. It substitutes every resolvable `${dotted.path}` marker (`${derived.*}`, `${provenance.*}`, `${as_of}`, etc.) and leaves `${narrative:*}` markers, and any path it cannot resolve, verbatim; the latter are listed in `unresolved`. It rejects a document whose `kind` is not `finplan_snapshot`.
