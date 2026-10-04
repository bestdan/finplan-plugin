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

| Tool                    | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Parameters                                                                                                          |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `describe_state_schema` | Return the JSON Schema for a finplan_state document, including every nested $def (PeriodRate/ReturnPeriod rate types and enums such as property_type) plus the schema fingerprint. Fetch it once to author a valid state in a single pass instead of discovering required fields from validation errors.                                                                                                                                                                                                   | (no parameters)                                                                                                     |
| `get_sample_profile`    | Load the Larsons fictional demo household (finplan_state document) via the file-response URL pattern, without the JSON entering context.                                                                                                                                                                                                                                                                                                                                                                   | (no parameters)                                                                                                     |
| `manage_state`          | Manage user state: create and modify financial profiles (person, accounts, goals, income, expenses). update_account can earmark an account to a goal via goal_id and surfaces dangling/orphaned earmark warnings; adding a goal via update_goal establishes a backing account (auto-creates a provisional savings account for dedicated-savings goals, or offers eligible accounts to link for retirement/education). Account payloads are validated against the Account schema before they are persisted. | action (create\|update_account\|update_goal\|update_person\|update_income_stream\|update_expense), state_json?, ... |
| `migrate_state`         | Upgrade a finplan_state document to the current schema once and return it as a downloadable file (urls.data) plus a compact summary, never inline. Re-stamps kind and schema_fingerprint so the persisted document stops re-migrating on every build_snapshot. Persist the download via /finplan:save-state; subsequent builds then report migrated: false.                                                                                                                                                | state_json                                                                                                          |

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

## Tools

### manage_state

State management tool for creating and modifying user state.

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

You already hold the full state (you passed it in as `state_json`). To rebuild the document, apply `changed.item` to the section named in `changed.section`: for list sections (`accounts`, `goals`, `income_streams`, `expenses`) update-or-append by id (`account_id` for accounts; `id` for the rest); for `person` replace `.person`. `/finplan:save-state` does this for you. `state_hash` is a SHA-256 over the resulting full document so you can verify the rebuild. Pass `return_full_state=true` to get the full UserState returned inline instead.

| Parameter            | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| -------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `action`             | string | `"create"`, `"update_account"`, `"update_goal"`, `"update_person"`, `"set_spouse"`, `"clear_spouse"`, `"update_income_stream"`, `"update_expense"`, `"remove_account"`, `"remove_goal"`, `"remove_income_stream"`, `"remove_expense"`                                                                                                                                                                                                                                                                              |
| `state_json`         | dict   | Current UserState JSON. Required for: update_account, update_goal, update_person, set_spouse, clear_spouse, update_income_stream, update_expense, remove_account, remove_goal, remove_income_stream, remove_expense.                                                                                                                                                                                                                                                                                               |
| `person_json`        | dict   | Person profile with fields: date_of_birth (YYYY-MM-DD), employment_status, annual_pretax_income_cents, marital_status, zipcode, optionally number_of_dependents. Also optional, and supplied together: `pia_cents_today_dollars` and `pia_source` — `estimate_social_security_pia_from_earnings_record` returns both, under the keys `pia_cents_today_dollars` and `source`. Required for: create, update_person.                                                                                                  |
| `spouse_json`        | dict   | Spouse profile (same fields as a person, the `pia_cents_today_dollars` / `pia_source` pair included — spousal and survivor benefits are computed against the spouse's own PIA). Unlike `person_json`, this payload fully **replaces** the stored spouse: one that omits the PIA pair drops it, so carry both forward when editing a saved spouse. Omitting `id` keeps the existing spouse's id; pass an explicit `id` to swap in a different person. The primary person must be married. Required for: set_spouse. |
| `account_json`       | dict   | Account from `create_account` result. Required for: update_account.                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `goal_json`          | dict   | Goal from `create_goal` result. Required for: update_goal.                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `income_stream_json` | dict   | Income stream from `create_income_stream` result. Required for: update_income_stream.                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `expense_json`       | dict   | Expense from `create_expense` result. Required for: update_expense.                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `account_id`         | string | `account_id` of the account to remove. Required for: remove_account.                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `goal_id`            | string | `id` of the goal to remove. Required for: remove_goal.                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `income_stream_id`   | string | `id` of the income stream to remove. Required for: remove_income_stream.                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `expense_id`         | string | `id` of the expense to remove. Required for: remove_expense.                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `return_full_state`  | bool   | When `true`, every mutating action (all actions except `create`) returns the full UserState inline instead of a delta (default `false`). Ignored by `create`.                                                                                                                                                                                                                                                                                                                                                      |

**Actions:**

- **create** — Create a new UserState with person profile. Requires `person_json`.
- **update_account** — Add or update an account in state. Requires `state_json` and `account_json`. If account has an 'account_id' field matching an existing account, it replaces it; otherwise adds new. Refuses (error `"Missing beneficiary"`) to add a `plan_529`, or move one off beneficiary ownership, unless `ownership_type` is `"beneficiary"`; a saved 529 that already lacked a beneficiary stays editable.
- **update_goal** — Add or update a goal in state. Requires `state_json` and `goal_json`. If goal has an 'id' field matching an existing goal, it replaces it; otherwise adds new. A goal's funded amount is account-derived, so **adding a new goal establishes a backing account**: dedicated-savings types (emergency fund, vacation, …) auto-create a provisional Taxable Savings account linked to the goal (returned as `provisional_account` with `assumptions` to confirm; an auto-create returns the full document, not a delta); retirement/education and ambiguous types instead return `eligible_accounts` to link plus a `warnings` entry that the goal is not yet funded. A multi-owner household defers the auto-create with a `warnings` entry + `candidate_owner_ids`. Editing an existing goal never re-runs establishment.
- **update_person** — Update (edit) person info in state. Requires `state_json` and `person_json` with fields to change.
- **set_spouse** — Set or replace the primary person's spouse. Requires `state_json` and `spouse_json` (a full person profile; omitting its `id` keeps the existing spouse's id, so editing spouse fields never changes identity and never orphans accounts that reference it). The primary person must be married — setting a spouse on a non-married person returns a structured "Only married persons can have spouse information" validation error and leaves state unchanged.
- **clear_spouse** — Remove the primary person's spouse. Requires `state_json`. Idempotent (clearing when there is no spouse still succeeds); does not cascade to the spouse's linked accounts.
- **update_income_stream** — Add or update an income stream in state. Requires `state_json` and `income_stream_json`. If income stream has an 'id' field matching an existing one, it replaces it; otherwise adds new.
- **update_expense** — Add or update an expense in state. Requires `state_json` and `expense_json`. If expense has an 'id' field matching an existing one, it replaces it; otherwise adds new.
- **remove_account** — Remove an account from state by `account_id`. Requires `state_json` and `account_id`.
- **remove_goal** — Remove a goal from state by `goal_id`. Requires `state_json` and `goal_id`.
- **remove_income_stream** — Remove an income stream from state by `income_stream_id`. Requires `state_json` and `income_stream_id`.
- **remove_expense** — Remove an expense from state by `expense_id`. Requires `state_json` and `expense_id`.

### describe_state_schema

Return the JSON Schema for a `finplan_state` document. Fetch it **once** to author a valid state in a single pass, instead of discovering required fields by submitting and reading validation errors. The schema describes every nested shape under `json_schema["$defs"]` — including the `PeriodRate` / `ReturnPeriod` rate types and all enums such as `property_type` — so you don't have to probe level-by-level.

Takes no parameters. Returns `{kind, schema_fingerprint, json_schema}`. The result is static for a given server version and safe to cache; `schema_fingerprint` identifies the schema version a document must match.

### get_sample_profile

Load the Larsons — a fictional demo household — without the state document entering context. Takes no parameters. Returns a `FileResponse`: the full `finplan_state` JSON at `urls.data`, a schema + jq examples at `urls.schema`, and a compact `summary` (household label, marital status, account/goal/income/expense counts, goal names). `note` flags the data as fictional and suggests follow-up calls (e.g. a Monte Carlo retirement projection for Mark at 62, federal + NY tax filing jointly, Social Security claiming ages 62/67/70, both 529 goals). Never merge this document into a real user's state.

### migrate_state

Upgrade a state document to the current schema **once** and hand it back as a download. An unstamped or stale document makes every `build_snapshot` re-migrate it; this runs the shared ingest path (validate → migrate → stamp `kind` + `schema_fingerprint`), writes the upgraded document to file storage, and returns a download URL plus a compact summary — never the full document inline. Persist the downloaded document (e.g. via `/finplan:save-state`); subsequent `build_snapshot` calls then see a conformant document and report `migrated: false`, ending the re-migration loop.

| Parameter    | Type | Description                                                                                                          |
| ------------ | ---- | -------------------------------------------------------------------------------------------------------------------- |
| `state_json` | dict | A `finplan_state` document to upgrade. May be unstamped or stale; it is validated and re-stamped on the way through. |

Returns `{success, urls, summary}` on success — the migrated document lives at `urls.data`, and `summary` carries `kind`, `schema_hash`, `migrated`, `schema_drift`, and `warnings`. Returns an error envelope with structured `errors` when the document cannot validate.

### link_account

Persist external-sync crosswalk links onto FinPlan accounts so a Monarch↔FinPlan link is confirmed **once** and every later sync matches deterministically on `external_id`. Batch and many-to-one (several source ids onto one FinPlan account); appending an already-linked id is a no-op. The whole batch fails (nothing persisted) if any `finplan_account_id` is unknown, if an id is already linked to a different account, or if the account is already linked to a different `system`. Returns the linked-account summaries and a new `state_ref`.

| Parameter    | Type   | Description                                                                                                                   |
| ------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `links`      | list   | Links to persist, each `{finplan_account_id, external_ids}` (external_ids is a list of source ids mapping onto that account). |
| `state_json` | dict   | Inline planning-state document (provide exactly one of state_json, state_ref).                                                |
| `state_path` | string | (local transport only; not accepted on the hosted server — use `state_json` or `state_ref`)                                   |
| `state_ref`  | string | Handle to an already-uploaded state document (one-of).                                                                        |
| `system`     | string | The external source system being linked (default: monarch).                                                                   |

### unlink_account

Remove some or all external-sync crosswalk links from a FinPlan account. With `external_ids`, only those ids are removed; omitting them clears the account's link entirely. Scoped to one `system`; a no-op (wrong system, or ids not present) succeeds without churning state. Returns the remaining link state, a `changed` flag, and a `state_ref`.

| Parameter            | Type   | Description                                                                                 |
| -------------------- | ------ | ------------------------------------------------------------------------------------------- |
| `finplan_account_id` | string | The FinPlan account to unlink.                                                              |
| `state_json`         | dict   | Inline planning-state document (provide exactly one of state_json, state_ref).              |
| `state_path`         | string | (local transport only; not accepted on the hosted server — use `state_json` or `state_ref`) |
| `state_ref`          | string | Handle to an already-uploaded state document (one-of).                                      |
| `external_ids`       | list   | Source ids to remove; omit to clear the account's crosswalk entirely (default: none).       |
| `system`             | string | The external source system to unlink (default: monarch).                                    |

### reconcile_with_monarch

Reconcile a Monarch account pull against FinPlan state. Translates and gates each raw Monarch account, diffs it against the state's accounts via the persisted crosswalk, and reports four buckets: `matched` balance deltas, `only_in_monarch` (READY adds with no FinPlan link), `only_in_finplan` (accounts no candidate carried — reported, never touched), and `held_back` (items the gate couldn't accept, e.g. an unmodeled mortgage — surfaced, never dropped). With `confirm=False` (default) it writes nothing and returns an `apply_preview` of what the apply would do per each account's `sync_policy`; with `confirm=True` it applies the matched deltas (`live` overwritten, `estimate` overwritten but flagged noisy, `manual` skipped), persists the new state, and returns the `apply_report` plus a new `state_ref`. A re-run dry run after a confirm shows no residual drift on the applied accounts (idempotent).

| Parameter               | Type   | Description                                                                                          |
| ----------------------- | ------ | ---------------------------------------------------------------------------------------------------- |
| `monarch_accounts_json` | list   | Raw Monarch GetAccounts items (each `{id, type, balance, name?}`) to reconcile against the state.    |
| `state_json`            | dict   | Inline planning-state document (provide exactly one of state_json, state_ref).                       |
| `state_path`            | string | (local transport only; not accepted on the hosted server — use `state_json` or `state_ref`)          |
| `state_ref`             | string | Handle to an already-uploaded state document (one-of).                                               |
| `confirm`               | bool   | False (default) = dry-run diff + apply_preview, no writes; True = apply per sync_policy and persist. |
| `synced_on`             | string | Sync date (YYYY-MM-DD) stamped onto each refreshed account's source.last_synced; defaults to today.  |

### exclude_account

Record external accounts as knowingly excluded from the modeled state (batch). Use it when an `only_in_monarch` (or held-back) account is one the user deliberately won't model — a mortgage, a spouse's account, an extra card. Each exclusion is written onto `UserState.excluded_external_accounts` keyed on `(system, external_id)`, so every snapshot/check-in surfaces "seen in Monarch, not modeled" and a later `reconcile_with_monarch` stops re-proposing it as an add or held-back item. Idempotent: re-excluding the same key refreshes its record. Returns the recorded exclusions and a new `state_ref`.

| Parameter    | Type   | Description                                                                                 |
| ------------ | ------ | ------------------------------------------------------------------------------------------- |
| `exclusions` | list   | Accounts to exclude, each `{external_id, label, reason, last_seen_balance_cents?}`.         |
| `state_json` | dict   | Inline planning-state document (provide exactly one of state_json, state_ref).              |
| `state_path` | string | (local transport only; not accepted on the hosted server — use `state_json` or `state_ref`) |
| `state_ref`  | string | Handle to an already-uploaded state document (one-of).                                      |
| `system`     | string | The external source system the exclusions belong to (default: monarch).                     |

### complete_synced_account

Complete a held-back mortgage/real-estate account (surfaced as `needs_manual_input` in `reconcile_with_monarch`'s `held_back` bucket) with the loan terms / property details the source can't supply, plus the ownership it omits, then write it. The candidate is re-identified from the fresh `monarch_accounts_json` by `external_id` (never a stale copy), so balance/name/type stay current; the account is validated like `create_account` and written carrying its `source` provenance (stamped `last_synced`), so a later `reconcile_with_monarch` matches it. It's a no-op (writes nothing) when the id is already linked, knowingly excluded, not in the latest pull, or not held back anymore; a mortgage missing `mortgage_terms_json` (or real estate missing `property_details_json`) is reported pending, never partially written. With `confirm=False` (default) it returns an `account_preview`; with `confirm=True` it appends the account and persists a new `state_ref`.

| Parameter               | Type   | Description                                                                                          |
| ----------------------- | ------ | ---------------------------------------------------------------------------------------------------- |
| `monarch_accounts_json` | list   | Raw Monarch GetAccounts items (each `{id, type, balance, name?}`); the candidate is re-found here.   |
| `external_id`           | string | The source id of the held-back account to complete (from a prior `held_back` entry).                 |
| `ownership_json`        | dict   | Account ownership (required — the source omits it): `{ownership_type, owner_ids, beneficiary_id?}`.  |
| `mortgage_terms_json`   | dict   | Mortgage loan terms (required for a `mortgage`; same shape as `create_account`).                     |
| `property_details_json` | dict   | Property details (required for a `real_estate` account; same shape as `create_account`).             |
| `state_json`            | dict   | Inline planning-state document (provide exactly one of state_json, state_ref).                       |
| `state_path`            | string | (local transport only; not accepted on the hosted server — use `state_json` or `state_ref`)          |
| `state_ref`             | string | Handle to an already-uploaded state document (one-of).                                               |
| `system`                | string | The external source system the external_id belongs to (default: monarch).                            |
| `confirm`               | bool   | False (default) = validate + return account_preview, no writes; True = append the account + persist. |
| `synced_on`             | string | Sync date (YYYY-MM-DD) stamped onto the created account's source.last_synced; defaults to today.     |

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
