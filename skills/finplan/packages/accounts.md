# Account Tools

Financial account types, allocations, ownership, and creation.

<!-- BEGIN GENERATED: tool-index accounts -->

## Tool index

| Tool                                    | Description                                                                                                                            | Parameters                                                                                                                                                                                                                                                                                                                                                                                            |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `create_account`                        | Create a financial account with balance, ownership, and allocation.                                                                    | account_type, balance_cents, ownership_json, allocation_json?, tax_treatment?, name?, institution?, account_number_last4?, is_current_employer?, employer_match_json?, mortgage_terms_json?, property_details_json?, loan_terms_json?, goal_id?, monthly_contribution_cents\|contribution_schedule_json?, plan_state?, opened_date?, plan_max_balance_cents?, contribution_basis_cents?, donor_count? |
| `get_account_limits`                    | Get limits for an account type: contribution limit with age catch-up (401k, IRA, HSA, SEP, SIMPLE), 529 gift-tax exclusion, FDIC, RMD. | account_type, birth_year?, year?, age?, hsa_coverage?, simple_small_employer?                                                                                                                                                                                                                                                                                                                         |
| `get_allowed_asset_classes_for_account` | Get the asset classes (stocks, bonds, cash, crypto, real estate, other) allowed for a specific account type.                           | account_type                                                                                                                                                                                                                                                                                                                                                                                          |
| `list_account_types`                    | List all valid account_type string values with short descriptions.                                                                     | (no parameters)                                                                                                                                                                                                                                                                                                                                                                                       |

<!-- END GENERATED: tool-index accounts -->

## Tools

### create_account

Valid `account_type` values are in [reference-data.md](reference-data.md#account-types), or call `list_account_types`.

Ownership must be specified via `ownership_json` with required fields `ownership_type` (`"individual"`, `"joint"`, or `"beneficiary"`) and `owner_ids` (list of person IDs), and optionally `beneficiary_id` (required for beneficiary type). Example: `{"ownership_type": "individual", "owner_ids": ["person-123"]}`.

Every `plan_529` account must name a beneficiary: use `"beneficiary"` ownership with the student's `beneficiary_id`, adding the student as a dependent first if needed. Example: `{"ownership_type": "beneficiary", "owner_ids": ["person-123"], "beneficiary_id": "dependent-456"}`. Ask the user who the 529 is for. If there is no student yet, the owner can name themselves (their own id as `beneficiary_id`) and change the beneficiary later; mention that a change may restart the 15-year clock for rolling the 529 into a Roth IRA. `create_account` refuses a 529 without it, and so does `manage_state` `update_account` when it adds a 529 or moves one off beneficiary ownership. A saved 529 that already lacks a beneficiary still loads and stays editable, with a warning.

Allocation can optionally be specified via `allocation_json` with fields `stocks_pct`, `bonds_pct`, `cash_pct`, `crypto_pct`, `real_estate_pct`, and `other_pct` (all integers 0-100 that sum to 100; `stocks_pct`, `bonds_pct`, and `cash_pct` are required, while `crypto_pct`, `real_estate_pct`, and `other_pct` default to 0 if omitted). Example: `{"stocks_pct": 60, "bonds_pct": 30, "cash_pct": 10}`. If omitted, it defaults to 100% cash for cash-only account types (cash accounts, `mortgage`, and the loan types `credit_card`, `student_loan`, `auto_loan`, `personal_loan`, `other_loan`) and to 100% `real_estate_pct` for `real_estate`. It is required for every other type.

Optionally specify `tax_treatment` to include a tax profile in the response.

Type-specific inputs:

- `employer_match_json`: only valid on a current-employer 401k (`account_type` is `traditional_401k`/`roth_401k` and `is_current_employer` is true); rejected otherwise. Must include `formula_type`. For `"tiered"` add `tiers`; for `"non_elective"` set `non_elective_pct`.
- `mortgage_terms_json`: required for `mortgage`, ignored otherwise. Must include `original_principal_cents`, `interest_rate` (annual decimal), `term_months`, `origination_date` (ISO 8601), and `monthly_payment_cents` (principal + interest only). Optional `is_fixed_rate` (default true).
- `property_details_json`: required for `real_estate`, ignored otherwise. Must include `property_type`, `purchase_price_cents`, and `purchase_date` (ISO 8601). Optional: `estimated_value_cents`, `appreciation_rate`, `building_type`, `city`, `state`, `zip`, `linked_mortgage_account_id`.
- `loan_terms_json`: required for `credit_card`, `student_loan`, `auto_loan`, `personal_loan`, `other_loan`, ignored otherwise. Must include `apr` (annual decimal) and `minimum_payment_cents`. Optional `term_months`: set for an amortizing installment loan, omit for revolving debt like a credit card.
- `goal_id` earmarks the account to a goal; the goal's funded amount then derives from this account's balance.
- `monthly_contribution_cents`: set it when the honest per-account contribution is known (e.g. an IRA at its annual cap, a taxable account taking no new money) so `project_plan` honors it as a fixed monthly amount instead of splitting the household surplus by balance; the remaining surplus is split by balance across the accounts without a pin. Non-negative; omit for the balance-weighted split. Inert on liability/real-estate accounts.
- `contribution_schedule_json`: the start/stop/grow counterpart to `monthly_contribution_cents`, mutually exclusive with it, e.g. "max the IRA at $583/mo until 2035, then stop". Fields: `monthly_amount_cents` (required), optional `start_date`/`end_date` (ISO; zero outside the window), `annual_growth_rate` (0-1, compounded from the projection start), and `real_terms` (grossed up by inflation). A bare `{"monthly_amount_cents": N}` equals the scalar pin.
- 529 only: `plan_state` (two-letter sponsoring state, decides eligibility for an in-state-only state tax benefit); `opened_date` (YYYY-MM-DD the current beneficiary's Roth-rollover clock started: when the account was opened, or the last change of beneficiary if later); `plan_max_balance_cents` (the plan's per-beneficiary aggregate limit from the plan disclosure, positive); `contribution_basis_cents` (remaining contribution basis, from the plan statement or provider; omit when unknown, never estimate it); `donor_count` (at least 1; omit to count the account owners, plus the spouse on a joint household).

### get_account_limits

Returns FDIC insurance, RMD requirements, purchase limits and early withdrawal penalties under `limits`, and the annual contribution limit under `contribution_limit` for a 401(k), IRA, Roth IRA, HSA, SEP-IRA or SIMPLE IRA: base limit, catch-up tier and amount for the owner's age, total, and `is_projected` for a year past the published IRS table. `contribution_limit` is null for other types. A 529 returns `plan_529_gift_tax` instead: the per-donor annual gift-tax exclusion and the five-year superfunding election.

- `birth_year` corrects RMD start age per SECURE 2.0 (72 if born before 1951, 73 for 1951-1959, 75 for 1960 or later) and sets the catch-up age when `age` is omitted. Omit for the default age 73.
- `year` is the tax year for the contribution limit, 2024 or later; defaults to the current year.
- `age` is the owner's age at December 31 of `year` and sets the catch-up tier. Omit both `age` and `birth_year` for the limit without catch-up.
- `hsa_coverage` (HSA only): `self_only` or `family` (default `family`).
- `simple_small_employer` (SIMPLE IRA only): true for an employer with 25 or fewer employees (or 26-100 electing the higher contribution), which raises the limit. Omitted: the higher total.
