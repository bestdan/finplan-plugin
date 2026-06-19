---
description: Read a saved FinPlan snapshot from snapshots/<as_of>/snapshot.json using targeted jq queries to minimize token usage
allowed-tools: Bash(jq *)
argument-hint: [latest | <as_of>] [section]
---

# Read Financial Plan Snapshot

Read a saved snapshot from the local `snapshots/` directory with minimal token usage.
Snapshots live at `snapshots/<as_of>/snapshot.json`, one immutable file per check-in date.

## Arguments

`$ARGUMENTS` selects **which** snapshot and **what** section:

| Position | Argument               | Meaning                                                              |
| -------- | ---------------------- | -------------------------------------------------------------------- |
| 1st      | _(empty)_ or `latest`  | The most recent snapshot — the one with the greatest `as_of` field   |
| 1st      | `<as_of>` (YYYY-MM-DD) | The snapshot for that specific date                                  |
| 2nd      | _(empty)_              | A compact summary (default — see below)                              |
| 2nd      | a dotted path          | Just that subtree, e.g. `derived.net_worth`, `provenance`, `derived` |

`latest` resolves against each snapshot's own `as_of` field, so the chosen record can't
disagree with the date written inside it. Everything runs through `jq` — no `ls`/`cat`.

## How to use

Two fixed jq fragments are reused below; substitute them verbatim where named (they are
constant program text, not user input):

- `SUMMARY` (the default compact object):
  `{as_of, net_worth_cents: .derived.net_worth.net_worth_cents, by_category: .derived.by_category, allocation: .derived.allocation, captured_at: .provenance.captured_at, staleness_days: .provenance.staleness_days, finplan_version: .provenance.finplan_version}`
- `LATEST` (streams the snapshots, keeping only the greatest `as_of` — one record in
  memory at a time, since each embeds a full `facts` state):
  `reduce inputs as $s (null; if . == null or $s.as_of > .as_of then $s else . end)`

1. **Pick the section** from the 2nd argument:
   - _(empty)_ → use `SUMMARY`.
   - a dotted path (e.g. `derived.net_worth`, `provenance`) → pass it as data with
     `--arg sel '<path>'` and resolve with `getpath($sel | split("."))`. Never splice the
     path into the program text — `--arg` keeps it from being interpreted as a jq filter.

2. **Run the jq query** for the requested snapshot:

   - `latest` (or empty 1st arg), default summary:

         jq -n 'LATEST | SUMMARY' snapshots/*/snapshot.json

   - `latest`, a section:

         jq -n --arg sel 'derived.net_worth' 'LATEST | getpath($sel | split("."))' snapshots/*/snapshot.json

   - a specific `<as_of>`, default summary:

         jq 'SUMMARY' snapshots/<as_of>/snapshot.json

   - a specific `<as_of>`, a section:

         jq --arg sel 'provenance' 'getpath($sel | split("."))' snapshots/<as_of>/snapshot.json

   If jq reports no input files (no snapshot exists), or the named `<as_of>` file is
   missing, tell the user and suggest building and saving one with `build_snapshot` +
   `/finplan:save-snapshot`.

## Important

- Always use `jq` — never `cat` or the Read tool on the snapshot file, to avoid loading
  the full JSON (it embeds a complete `facts` state) into context.
- For the default summary, present money fields as dollars (divide cents by 100) in a
  readable form.
- Snapshots are read-only history; this command never modifies them.
