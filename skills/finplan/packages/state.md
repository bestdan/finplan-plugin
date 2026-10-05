# Profile & State Tools

Person profiles and user state management.

Persistence (save/load) is handled client-side via slash commands (`/finplan:read-state`, `/finplan:save-state`), not by the MCP server. These commands are bundled with the FinPlan plugin.

**Reading efficiently:** `/finplan:read-state` reads via targeted `jq` so the full document never enters context. Beyond single sections it supports **multi-section fetch** (`sections accounts,goals` → one object) and **derived rollups** — `balances-by-type`, `goals-by-status`, and `net-worth` (financial-assets / real-estate / liabilities). Prefer these over pulling whole `accounts`/`goals` arrays to compute a total by hand.

**State-ref reuse:** A tool response may include a `state_ref` (`st_…`) for its canonical
state document. Pass it back as `state_ref`, or as `base.state_ref` for scenario tools,
instead of inlining the full state again. Refs have an approximately 60-minute sliding TTL
that refreshes on each successful use. If a call returns `state_ref_expired`, re-send the
full `state_json` in that same call.

<!-- BEGIN GENERATED: tool-index state -->

## Tool index: state

| Tool                    | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Parameters                                                                                                                                                                                                                                                                           |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `describe_state_schema` | Return the JSON Schema for a finplan_state document, including every nested $def (PeriodRate/ReturnPeriod rate types and enums such as property_type) plus the schema fingerprint. Fetch it once to author a valid state in a single pass instead of discovering required fields from validation errors.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | (no parameters)                                                                                                                                                                                                                                                                      |
| `get_sample_profile`    | Load the Larsons fictional demo household (finplan_state document) via the file-response URL pattern, without the JSON entering context.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | (no parameters)                                                                                                                                                                                                                                                                      |
| `manage_state`          | Manage user state: create and modify financial profiles (person, accounts, goals, income, expenses). update_account can earmark an account to a goal via goal_id and surfaces dangling/orphaned earmark warnings; update_income_stream backs a goal with income via goal_id + funding_role (contribution or offset, with an optional allocation slice), confirms the link, and warns when clearing one leaves the goal with no account or income backing; a goal is backed by a linked account or a linked income stream, and adding a goal via update_goal with no backing establishes a backing account (auto-creates a provisional savings account for dedicated-savings goals, or offers eligible accounts to link for retirement/education). Account payloads are validated against the Account schema before they are persisted. | action (create\|update_account\|update_goal\|update_person\|update_income_stream\|update_expense), state_json?, person_json?, spouse_json?, account_json?, goal_json?, income_stream_json?, expense_json?, account_id?, goal_id?, income_stream_id?, expense_id?, return_full_state? |
| `migrate_state`         | Upgrade a finplan_state document to the current schema once and return it as a downloadable file (urls.data) plus a compact summary, never inline. Re-stamps kind and schema_fingerprint so the persisted document stops re-migrating on every build_snapshot. Persist the download via /finplan:save-state; subsequent builds then report migrated: false.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | state_json                                                                                                                                                                                                                                                                           |

<!-- END GENERATED: tool-index state -->

<!-- BEGIN GENERATED: tool-index sync -->

## Tool index: sync

| Tool                      | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Parameters                                                                                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `complete_synced_account` | Complete a held-back mortgage/real-estate account (needs_manual_input from reconcile_with_monarch) with user-supplied loan terms / property details plus ownership, then write it carrying source provenance. Re-identifies the candidate from the fresh Monarch pull by external_id; a no-op when already linked, not in the pull, or no longer held back; missing terms reported pending, never partially written. confirm=False previews; confirm=True persists. | monarch_accounts_json, external_id, ownership_json, mortgage_terms_json?, property_details_json?, state_json\|state_path\|state_ref, system?, confirm?, synced_on? |
| `exclude_account`         | Record external accounts as knowingly excluded from the modeled state (batch): write each {external_id, label, reason, last_seen_balance_cents?} onto UserState.excluded_external_accounts so snapshots surface 'seen in Monarch, not modeled' and a later reconcile stops re-proposing it. Idempotent (re-excluding a key refreshes its record).                                                                                                                   | exclusions, state_json\|state_path\|state_ref, system?                                                                                                             |
| `link_account`            | Persist external-sync crosswalk links onto FinPlan accounts (batch): set or extend each account's AccountSource (system + external_ids) so a Monarch↔FinPlan link is confirmed once and every later sync matches on external_id. Idempotent; many-to-one (several source ids → one FinPlan account).                                                                                                                                                                | links, state_json\|state_path\|state_ref, system?                                                                                                                  |
| `reconcile_with_monarch`  | Reconcile a Monarch account pull against FinPlan state: dry-run the diff (matched balance deltas, only-in-Monarch adds, only-in-FinPlan accounts, held-back items) then, on confirm, apply the matched deltas honoring each account's sync_policy (live overwrite, estimate flagged-noisy, manual skipped) and persist a new state. Idempotent re-sync via the persisted crosswalk.                                                                                 | monarch_accounts_json, state_json\|state_path\|state_ref, confirm?, synced_on?                                                                                     |
| `unlink_account`          | Remove some or all external-sync crosswalk links from a FinPlan account: drop the given external_ids (or clear the account's AccountSource entirely). Scoped to one source system.                                                                                                                                                                                                                                                                                  | finplan_account_id, state_json\|state_path\|state_ref, external_ids?, system?                                                                                      |

<!-- END GENERATED: tool-index sync -->

## Tool notes

### manage_state

**Response shape:** `action="create"` returns the full UserState JSON (plus `success`, `message`, `state_hash`). The `update_*` actions return a **compact delta by default** — only the changed section plus a verification hash — instead of echoing the whole document back on every edit:

```json
{
  "success": true,
  "message": "...",
  "action": "update_account",
  "changed": { "section": "accounts", "item": { "...": "the changed entity" } },
  "state_hash": "sha256:...",
  "last_updated": "YYYY-MM-DD"
}
```

You already hold the full state (you passed it in as `state_json`). To rebuild the document, apply `changed.item` to the section named in `changed.section`: for list sections (`accounts`, `goals`, `income_streams`, `expenses`) update-or-append by id (`account_id` for accounts; `id` for the rest); for `person` replace `.person`. `/finplan:save-state` does this for you. `state_hash` is a SHA-256 over the resulting full document so you can verify the rebuild. Pass `return_full_state=true` to get the full UserState returned inline instead; every mutating action honors it, and `create` ignores it.

**Inputs:**

- `state_json` is required for every action except `create`.
- Each action has its own payload: `person_json` (create, update_person), `spouse_json` (set_spouse), `account_json`, `goal_json`, `income_stream_json`, `expense_json` (the matching `update_*`). Each `create_*` tool's result field is what goes in; see the [mutation sequence](#how-to-integrate-accounts-and-goals).
- The `remove_*` actions take the id of the thing to remove: `account_id`, `goal_id`, `income_stream_id`, `expense_id`.
- `person_json` carries `date_of_birth` (YYYY-MM-DD), `employment_status`, `annual_pretax_income_cents`, `marital_status`, `zipcode`, optionally `number_of_dependents`. For computed income tax it may carry `filing_status`, `residence_state` (two-letter code) and `residence_locality` (such as `"nyc"`), each null to derive (the locality is never derived; see [projection.md](projection.md#project_plan)). It may also carry `pia_cents_today_dollars` and `pia_source`, supplied together: `estimate_social_security_pia_from_earnings_record` returns both, under the keys `pia_cents_today_dollars` and `source`.
- `spouse_json` takes the same fields as a person, the PIA pair included; spousal and survivor benefits are computed against the spouse's own PIA. Unlike `person_json`, it fully **replaces** the stored spouse: one that omits the PIA pair drops it, so carry both forward when editing a saved spouse. Omitting `id` keeps the existing spouse's id; pass an explicit `id` to swap in a different person.

**Actions:**

- **update_account** — If the account has an `account_id` matching an existing account, it replaces it; otherwise adds new. Refuses (error `"Missing beneficiary"`) to add a `plan_529`, or move one off beneficiary ownership, unless `ownership_type` is `"beneficiary"`; a saved 529 that already lacked a beneficiary stays editable.
- **update_goal** — If the goal has an `id` matching an existing goal, it replaces it; otherwise adds new. A goal is backed by **≥1 linked account OR ≥1 linked income stream** — a goal already backed on either channel establishes nothing and gets no warning. **Adding a new goal with no backing establishes a backing account** (its funded amount is account-derived): dedicated-savings types (emergency fund, vacation, …) auto-create a provisional Taxable Savings account linked to the goal (returned as `provisional_account` with `assumptions` to confirm; an auto-create returns the full document, not a delta); retirement/education and ambiguous types instead return `eligible_accounts` to link plus a `warnings` entry that the goal has no backing (account or income). A multi-owner household defers the auto-create with a `warnings` entry + `candidate_owner_ids`. Editing an existing goal that is still unbacked re-runs establishment too, but only auto-creates an account when the edit changed the goal's type into a dedicated-savings (auto-create) type; a routine edit of an unbacked goal returns a `warnings` entry instead.
- **update_income_stream** — Replace by matching `id`; otherwise add new. **Back a goal with this income** by setting `goal_id` plus `funding_role` — `contribution` (accumulates toward the goal) or `offset` (reduces its spend-phase withdrawals, e.g. Social Security against a retirement drawdown) — optionally pinning the slice with `allocation_amount_cents` **or** `allocation_percentage` (at most one, contribution only; an offset carrying either is rejected, and leaving both unset means the whole stream backs the goal, unsliced). The payload replaces the whole stream, so resend `goal_id` to keep an existing link and omit it to clear one (the linkage keys are pruned). A link comes back as `income_link`: `{goal_id, goal_name, funding_role, allocation_basis (amount|percentage|unspecified|none), backing_after}`. Unlike an account earmark, an income link is a slice and never feeds the goal's funded amount, so `warnings` flags a stream pointing at a missing goal (dangling) and a cleared link only when it leaves the goal with **no account and no income** backing.
- **remove_income_stream** — Never cascades; removing a stream that backed a goal reports the same `warnings` entry as clearing its link, and only when the goal is left with **no account and no income** backing.
- **update_expense** — Replace by matching `id`; otherwise add new.
- **update_person** — `person_json` carries only the fields to change.
- **set_spouse** — The primary person must be married; setting a spouse on a non-married person returns a structured "Only married persons can have spouse information" validation error and leaves state unchanged. Omitting the spouse's `id` keeps the existing id, so editing spouse fields never changes identity and never orphans accounts that reference it.
- **clear_spouse** — Idempotent (clearing when there is no spouse still succeeds); does not cascade to the spouse's linked accounts.

### describe_state_schema

Fetch it **once** to author a valid state in a single pass, instead of discovering required fields by submitting and reading validation errors. Every nested shape is under `json_schema["$defs"]`. The result is static for a given server version and safe to cache; `schema_fingerprint` identifies the schema version a document must match.

### get_sample_profile

Returns a `FileResponse` (the state at `urls.data`, a schema + jq examples at `urls.schema`), so the state document never enters context. `note` flags the data as fictional. Never merge this document into a real user's state.

### migrate_state

An unstamped or stale document makes every `build_snapshot` re-migrate it. This runs the shared ingest path once and returns a download, never the full document inline. Persist the downloaded document (e.g. via `/finplan:save-state`); subsequent `build_snapshot` calls then report `migrated: false`. The migrated document is at `urls.data`; an error envelope with structured `errors` comes back when the document cannot validate.

## Monarch sync tools

The sync tools take the state as exactly one of `state_json`, `state_ref` (`state_path` is local transport only and not accepted on the hosted server). `system` (on `link_account`, `unlink_account`, `exclude_account`, and `complete_synced_account`) defaults to `monarch`, and `synced_on` (YYYY-MM-DD, on `reconcile_with_monarch` and `complete_synced_account`) defaults to today. Tools that persist return a new `state_ref`.

### link_account

Confirms a Monarch↔FinPlan link **once**, so every later sync matches deterministically on `external_id`. Batch and many-to-one (several source ids onto one FinPlan account); appending an already-linked id is a no-op. The whole batch fails (nothing persisted) if any `finplan_account_id` is unknown, if an id is already linked to a different account, or if the account is already linked to a different `system`.

### unlink_account

With `external_ids`, only those ids are removed; omitting them clears the account's link entirely. A no-op (wrong system, or ids not present) succeeds without churning state.

### reconcile_with_monarch

Reports four buckets: `matched` balance deltas, `only_in_monarch` (READY adds with no FinPlan link), `only_in_finplan` (accounts no candidate carried — reported, never touched), and `held_back` (items the gate couldn't accept, e.g. an unmodeled mortgage — surfaced, never dropped). With `confirm=False` (default) it writes nothing and returns an `apply_preview`; with `confirm=True` it applies the matched deltas per each account's `sync_policy` (`live` overwritten, `estimate` overwritten but flagged noisy, `manual` skipped), persists, and returns the `apply_report`. A re-run dry run after a confirm shows no residual drift on the applied accounts (idempotent).

### exclude_account

Use it when an `only_in_monarch` (or held-back) account is one the user deliberately won't model — a mortgage, a spouse's account, an extra card. Each exclusion is keyed on `(system, external_id)`, so every snapshot/check-in surfaces "seen in Monarch, not modeled" and a later `reconcile_with_monarch` stops re-proposing it. Idempotent: re-excluding the same key refreshes its record.

### complete_synced_account

Completes a held-back account (`needs_manual_input` in `reconcile_with_monarch`'s `held_back` bucket) with the loan terms / property details and ownership the source omits. The candidate is re-identified from the fresh `monarch_accounts_json` by `external_id` (never a stale copy). `ownership_json` is required; `mortgage_terms_json` is required for a `mortgage` and `property_details_json` for a `real_estate` account, in the same shape as `create_account`. A mortgage missing its terms (or real estate missing its details) is reported pending, never partially written. It is a no-op (writes nothing) when the id is already linked, knowingly excluded, not in the latest pull, or not held back anymore. `confirm=False` (default) returns an `account_preview` and writes nothing; `confirm=True` appends the account and persists.

## Typical workflow

1. `/finplan:read-state` to load existing state from local file (or skip if starting fresh)
2. `manage_state` with `action: "create"` and `person_json` to set up the profile, then `/finplan:save-state`
3. Integrate each account, goal, income stream, and expense with the [mutation sequence](#how-to-integrate-accounts-and-goals) below
4. `/finplan:read-state` to resume in future sessions

## State Persistence Rules

**CRITICAL**: Save the user state file after EVERY change using `/finplan:save-state`. The local state file is the source of truth.

### When to save

Call `/finplan:save-state` immediately after:

- Creating a new user state
- Adding or updating an account in the state (via `action="update_account"`)
- Adding or updating a goal in the state (via `action="update_goal"`)
- Adding or updating an income stream in the state (via `action="update_income_stream"`)
- Adding or updating an expense in the state (via `action="update_expense"`)
- Updating person information (via `action="update_person"`)
- Setting or clearing the spouse (via `action="set_spouse"` / `action="clear_spouse"`)
- Any time the user provides new financial information

### How to integrate accounts and goals

Every object a `create_*` tool returns is lost until it is integrated into state. For each one:

1. **Create** — call the `create_*` tool.
2. **Integrate** — call `manage_state` with the matching `update_*` action, your current full state as `state_json`, and the created object under its key:

   | Create with            | `action`                 | Pass the created object as                       |
   | ---------------------- | ------------------------ | ------------------------------------------------ |
   | `create_account`       | `"update_account"`       | `account_json` ← its `account` field             |
   | `create_goal`          | `"update_goal"`          | `goal_json` ← its `goal` field                   |
   | `create_income_stream` | `"update_income_stream"` | `income_stream_json` ← its `income_stream` field |
   | `create_expense`       | `"update_expense"`       | `expense_json` ← its `expense` field             |

3. **Rebuild full state** — the response is normally a delta (see [manage_state](#manage_state)): apply `changed.item` to the section named in `changed.section`. It is the full document instead when you passed `return_full_state=true`, when the input was migrated, or when `update_goal` auto-created a provisional account — then use it directly. `/finplan:save-state` handles either shape for you.
4. **Save** — call `/finplan:save-state`, then continue from the rebuilt state for the next object.

For example, integrating a new account — `manage_state` with these arguments:

```json
{
  "action": "update_account",
  "state_json": { "...": "your current full state" },
  "account_json": { "...": "the account field from create_account" }
}
```

### Common mistakes

1. **Creating accounts/goals/income/expenses without adding to state** - They will be lost
2. **Forgetting to save after changes** - Changes won't persist between sessions. Always call `/finplan:save-state`.
3. **Saving only at the end** - If session ends early, data is lost
