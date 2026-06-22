---
description: Scaffold a snapshots/ check-in workspace (README, index, reference template) — idempotent
allowed-tools:
  - Write
  - Bash(test *)
  - Bash(mkdir *)
  - Bash(ls *)
  - mcp__finplan__get_checkin_template
argument-hint: [--force]
---

# Initialize Check-In Workspace

Lay down the one-time directory skeleton that the recurring `/finplan:checkin` procedure writes
into. This command only creates the **scaffold** — the README, the regenerable index, and a
reference copy of the check-in template. It never builds, saves, or fills a snapshot (that's
`/finplan:checkin`), and it never writes any strategic narrative or decision queue (that's the
user's layer).

Run it from the directory where the user keeps their financial files (the same directory their
`*_finplan_state.json` lives in), so `snapshots/` sits beside the state file.

## What it creates

All paths are relative to the current working directory:

- `snapshots/` — the workspace directory (one immutable `snapshots/<as_of>/` per check-in lands
  here over time).
- `snapshots/README.md` — the procedure: what a check-in is and how to run it.
- `snapshots/index.md` — a regenerable index of check-ins, maintained oldest-first (empty table to
  start).
- `snapshots/checkin.template.md` — a **reference** copy of the canonical check-in template, for
  the user to read. This copy is a point-in-time convenience only; `/finplan:checkin` always
  fetches the live template fresh via the `get_checkin_template` MCP tool so the fill can't drift
  as the snapshot schema evolves.

## Idempotency guard

Before writing anything, check whether the scaffold already exists:

```bash
test -e snapshots/README.md
```

- If it exists and `$ARGUMENTS` does **not** contain `--force`, **refuse**: tell the user a
  check-in workspace already exists here and that `--force` is required to re-lay the scaffold.
  Do not write.
- If it exists and `--force` is present, proceed — but only ever overwrite the three scaffold
  files below. **Never** touch existing `snapshots/<date>/` directories; those are immutable
  history and re-initializing must not clobber a single saved snapshot or check-in note.
- If it does not exist, proceed.

## Steps

1. Create the directory: `mkdir -p snapshots`.

2. Write `snapshots/README.md` with this content (the procedure the user follows each period):

   ````markdown
   # Financial check-ins

   This directory holds your periodic financial check-ins. Each check-in is an immutable,
   point-in-time record plus a short note you write about what it means.

   ## Layout

   - `snapshots/<YYYY-MM-DD>/snapshot.json` — the immutable facts record for that date
     (net worth, allocation, account/category rollups, income, goal funding). Written once;
     never edit it by hand.
   - `snapshots/<YYYY-MM-DD>/checkin.md` — the check-in note for that date. The facts are filled
     in for you; the `${narrative:*}` sections are yours to write.
   - `index.md` — a one-row-per-check-in summary, regenerated from the snapshots.
   - `checkin.template.md` — a reference copy of the note template (read-only; the live one is
     fetched fresh each run).

   ## Running a check-in

   From this directory (so your state file is found), run:

   ```
   /finplan:checkin
   ```

   It will, in order: warn you if your planning state is stale, build a snapshot for today, save
   it under `snapshots/<today>/`, diff it against your previous check-in, seed `checkin.md` with
   the current facts, and append a row to `index.md`.

   ## Facts vs. strategy — where you come in

   `/finplan:checkin` only ever writes **facts**. It never writes your strategic read. After it
   runs, open `snapshots/<today>/checkin.md` and fill the `${narrative:*}` sections — the
   headline, your goals-and-priorities assessment, the tax outlook, and open questions. That
   judgment is the point of the check-in, and only you write it.
   ````

3. Write `snapshots/index.md` with an empty index table:

   ```markdown
   # Check-in index

   Regenerable summary — one row per check-in, oldest first. Maintained by `/finplan:checkin`.

   | As of | Net worth | Allocation (stocks / bonds / cash) | State as of | Snapshot |
   | ----- | --------- | ---------------------------------- | ----------- | -------- |
   ```

4. Fetch the canonical template with the `get_checkin_template` MCP tool and write its `template`
   text verbatim to `snapshots/checkin.template.md`. If the tool call fails (server asleep or not
   authenticated), retry once; if it still fails, write the file with a single line noting the
   template could not be fetched and that `/finplan:checkin` will fetch it live anyway, then carry
   on — the reference copy is non-essential.

5. Confirm to the user: the files created (or overwritten under `--force`), and that the next step
   is to run `/finplan:checkin` from this directory.

## Important

- This command is scaffold-only — it does not call `build_snapshot`, save a snapshot, or write any
  `checkin.md` note. That is `/finplan:checkin`.
- Under `--force`, re-lay only the three scaffold files; never delete or overwrite anything under a
  `snapshots/<date>/` directory.
