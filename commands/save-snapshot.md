---
description: Save an immutable FinPlan snapshot JSON to snapshots/<as_of>/snapshot.json after building it
allowed-tools:
  - Write
  - Bash(test *)
argument-hint: [--force]
---

# Save Financial Plan Snapshot

Write an immutable point-in-time snapshot to the local file system. Snapshots are the
versioned, diffable twin of the mutable state file — once written for a date they are
historical fact, so this command **never overwrites silently**.

## Snapshot source

Use the most recent `build_snapshot` result from the current conversation. That tool
returns `{ success, snapshot }`; the `snapshot` object (top-level `kind`,
`snapshot_format_version`, `as_of`, `provenance`, `facts`, `derived`) is what gets
persisted — losslessly, in the canonical on-disk form described below.

If no `build_snapshot` result is available in this session, stop and tell the user to
build one first (`build_snapshot` over their current state via the MCP/CLI tools).

## Guard: must be a snapshot, not a state

Before writing, confirm the document's top-level `kind` is `"finplan_snapshot"`. If it is
anything else (e.g. `"finplan_state"`), **refuse** and tell the user this command only
saves snapshots — point them at `/finplan:save-state` for a state document.

## Storage layout

`snapshots/<as_of>/snapshot.json`, relative to the current working directory, where
`<as_of>` is the snapshot's own `as_of` date (`YYYY-MM-DD`). Never invent or override the
date — derive it from the snapshot so the path and the contents can't disagree.

## How to save

1. Read `<as_of>` from the snapshot's `as_of` field and form the path
   `snapshots/<as_of>/snapshot.json`.
2. Check whether that file already exists: `test -f snapshots/<as_of>/snapshot.json`.
   - If it exists and `$ARGUMENTS` does **not** contain `--force`, **refuse**: tell the
     user a snapshot already exists for that date and that `--force` is required to
     overwrite it. Do not write.
   - If it exists and `--force` is present, proceed (overwrite).
   - If it does not exist, proceed.
3. Write the snapshot JSON to the path with the Write tool in the canonical on-disk form
   — 2-space indentation, keys sorted (matching the engine's `snapshot_to_json`). Write
   parent directories as needed.
4. Confirm to the user: the path written, the `as_of` date, net worth from
   `derived.net_worth.net_worth_cents` (formatted as dollars), and whether this was a new
   write or a `--force` overwrite.

## Important

- Persist the snapshot losslessly — never drop, add, or alter a field or value. Only the
  formatting is canonicalized (2-space indent, sorted keys); the data is unchanged.
- A snapshot is immutable history; only ever overwrite on an explicit `--force`.
