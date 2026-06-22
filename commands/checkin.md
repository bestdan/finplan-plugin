---
description: Run a recurring financial check-in — build, save, and diff a snapshot, then seed the note
allowed-tools:
  - Read
  - Write
  - Bash(test *)
  - Bash(ls *)
  - Bash(jq *)
  - Bash(date *)
  - Skill(finplan:read-state)
  - Skill(finplan:read-snapshot)
  - Skill(finplan:save-snapshot)
  - mcp__finplan__build_snapshot
  - mcp__finplan__diff_snapshots
  - mcp__finplan__get_checkin_template
argument-hint: [as_of] [--force]
---

# Financial Check-In

Run one periodic check-in end to end: build an immutable snapshot for a date, save it, diff it
against the previous check-in, and seed the check-in note with the current facts. Run it from the
directory holding the user's `*_finplan_state.json` and the `snapshots/` workspace (created by
`/finplan:checkin-init` — if `snapshots/` doesn't exist, tell the user to run that first).

This command writes **facts only**. It never writes the strategic read — the `${narrative:*}`
sections of the note, and any decision queue or strategy doc, are the user's layer (see the final
section).

## Arguments

`$ARGUMENTS`:

- A bare `YYYY-MM-DD` sets the logical check-in date (`as_of`). Default: **today**
  (`date +%F`).
- `--force` allows overwriting an already-saved `snapshot.json` / `checkin.md` for that date.
  Without it, an existing snapshot for the date is immutable and the run refuses to clobber it.

## Procedure

Do these in order. Stop and report if any step fails before the snapshot is saved.

### 1. Warn if the planning state is stale

Find the state file (`*_finplan_state.json`, most recently modified if several) and read its
`last_updated` date — e.g. via `/finplan:read-state` or:

```bash
jq -r '.last_updated' <state-file>
```

Compute `staleness_days = as_of - last_updated` (whole days). If it exceeds ~90 days, warn the
user that the underlying state is stale and the snapshot will inherit that staleness — they may
want to run `/finplan:checkup` first to refresh balances. If it is negative (a backdated `as_of`
that precedes `last_updated`), the state is newer than this check-in date — report that rather than
a negative count, and don't warn. Surface the number either way, then
proceed (the warning does not block the check-in).

### 2. Build the snapshot

Call the `build_snapshot` MCP tool with the state document and `as_of` (default today). Keep the
returned `{ success, snapshot }` in the conversation — the next three steps consume it. If the
build fails, report the error and stop.

### 3. Save the snapshot (immutable)

Run `/finplan:save-snapshot` (pass `--force` through only if the user gave it). It writes the
snapshot from step 2 to `snapshots/<as_of>/snapshot.json`, deriving `<as_of>` from the snapshot
itself, and refuses to overwrite an existing file without `--force`. If it refuses, relay that and
stop — the date already has an immutable record.

### 4. Diff against the previous check-in

Find the most recent **prior** saved snapshot — the greatest `as_of` strictly less than this one:

```bash
ls -d snapshots/*/ 2>/dev/null
```

- If one exists, read its `snapshot.json` and call the `diff_snapshots` MCP tool with
  `old_snapshot_json` = the prior snapshot and `new_snapshot_json` = the one just built. Surface
  the structured delta to the user as a readable summary: net-worth change, allocation drift,
  notable category/account-type moves, and any goals or account types added or removed. Money
  deltas come back as integer cents (render as dollars); allocation deltas are percentage points.
- If there is no prior snapshot, tell the user this is the first check-in — there's nothing to
  diff against yet.

### 5. Fill and seed the check-in note

1. Fetch the canonical template fresh with the `get_checkin_template` MCP tool — **never** the
   bundled `snapshots/checkin.template.md` reference copy, which can drift from the schema.
2. Fill its `${...}` markers from the snapshot built in step 2, applying the generic filler rules:
   - `${dotted.path}` resolves against the snapshot JSON by walking keys (e.g.
     `${derived.net_worth.net_worth_cents}`, `${provenance.staleness_days}`, `${as_of}`).
   - A resolved path whose **leaf key ends in `_cents`** renders as a dollar amount: `$1,234.56`
     (value ÷ 100, thousands-separated, two decimals). Any other resolved scalar is stringified
     as-is (percent fields are already percentages).
   - `${narrative:*}` markers pass through **untouched** — they're the user's to write.
   - Any path that doesn't resolve, or that lands on an object/array rather than a scalar, is left
     in place verbatim (don't invent a value); note any such leftovers to the user.
3. Write the filled markdown to `snapshots/<as_of>/checkin.md`. If that file already exists, do
   **not** overwrite it without `--force` — the user may have already written narrative into it.

### 6. Update the index

Add one row to `snapshots/index.md` for this check-in, inserted in chronological position to keep
rows oldest-first (for a current-date check-in this is a plain append; a backdated `as_of` slots
in before later rows). The row has:

- `as_of` (the check-in date),
- net worth — `derived.net_worth.net_worth_cents` rendered as dollars,
- allocation — `derived.allocation.stocks_pct` / `bonds_pct` / `cash_pct`,
- state as of — `provenance.state_last_updated`,
- snapshot path — `snapshots/<as_of>/snapshot.json`.

If a row for this `as_of` already exists (a `--force` re-run), replace it in place rather than
adding a duplicate.

## Where you come in — facts vs. strategy

`/finplan:checkin` stops at the facts boundary. It seeds `checkin.md` with the numbers and leaves
every `${narrative:*}` section blank. After it runs, open `snapshots/<as_of>/checkin.md` and write
your strategic read: the headline, your goals-and-priorities assessment, the tax outlook, and open
questions. This command never writes that narrative, a decision queue, or any strategy content —
that judgment is yours.

## Important

- **Facts only.** Never fill a `${narrative:*}` section or write strategy/decision content.
- **Snapshots are immutable.** Only ever overwrite a saved `snapshot.json` or an existing
  `checkin.md` on an explicit `--force`.
- **Always fetch the template live** via `get_checkin_template`; the on-disk reference copy is for
  the user to read, not to fill from.
