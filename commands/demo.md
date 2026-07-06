---
description: Load the Larson family sample profile so you can try every FinPlan feature with zero real data
allowed-tools:
  - Bash(jq *)
  - Bash(cp *)
  - Bash(ls *)
  - Glob
  - Write
argument-hint: "[file-path]"
---

# Load the Sample Profile (the Larsons)

Load a complete fictional household — the Larsons — into a local state file so the user can try projections, taxes, Social Security, goals, and dashboards before entering any real numbers.

## Who the Larsons are

Married couple in Rochester, NY, filing jointly, two kids:

- **Mark** (43) — W-2 software engineer, $148,500/yr, 401(k) with employer match
- **Dana** (40) — self-employed designer, $87,000/yr, SEP-IRA
- **Ellie** (12) and **Sam** (9) — each with a 529 plan
- ~$799k across 8 financial accounts, plus a home and mortgage
- 5 goals: retirement at 62, two college funds, an emergency fund, and a kitchen renovation gated on the emergency fund being full

## Step 1: Check for an existing state file

Use Glob for `*finplan_state.json` in the current working directory.

- **If a state file exists**: STOP and warn the user — "You already have a FinPlan state file at `<path>`. Loading the sample would sit alongside your real data and could be picked up by other commands. Load the sample in a separate empty directory instead, or confirm you want to overwrite." Only proceed on explicit confirmation, and never silently overwrite.
- **If none exists**: proceed.

## Step 2: Copy the sample state

The sample ships with this plugin at `${CLAUDE_PLUGIN_ROOT}/data/larsons_finplan_state.json`. Copy it to the working directory (or to `$ARGUMENTS` if a path was given):

```bash
cp "${CLAUDE_PLUGIN_ROOT}/data/larsons_finplan_state.json" ./finplan_state.json
```

If `${CLAUDE_PLUGIN_ROOT}` is unavailable in your environment, fetch the same file from the public plugin repo instead: `https://raw.githubusercontent.com/bestdan/finplan-plugin/main/data/larsons_finplan_state.json`.

## Step 3: Confirm the load

Show a compact summary using jq (never read the whole file into context):

```bash
jq '{household: "the Larsons", accounts: (.accounts | length), goals: [.goals[].name], num_income_streams: (.income_streams | length), num_expenses: (.expenses | length)}' finplan_state.json
```

## Step 4: Suggest first questions

Tell the user the sample is loaded, then offer these five starters (all of which the Larsons' data answers well):

1. "Can the Larsons actually retire when Mark turns 62? Run a Monte Carlo projection."
2. "What's their federal + New York state tax bill this year, filing jointly with two kids?"
3. "Should Mark claim Social Security at 62, 67, or 70? Compare lifetime benefits."
4. "Are both 529s on track to cover four years of college each? Which kid is behind?"
5. "Build the projection dashboard so I can see every goal on one page."

## Wipe path

Make sure the user knows how to clear the sample before entering real data — this is fake data and must not blend into a real plan:

- **Delete it**: `rm finplan_state.json` (the sample lives only in this one local file; nothing is stored server-side).
- **Start real**: run `/finplan:setup` in a fresh directory (or after deleting the sample) to build their own plan.

## Important

- Never merge sample data into an existing state file.
- All amounts in the file are integer cents.
- The Larsons are fictional; any resemblance to real households is coincidental.
