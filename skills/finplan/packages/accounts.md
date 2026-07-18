# Account Tools

Financial account types, allocations, ownership, and creation.

## Tools

### create_account

Create a financial account with balance, ownership, and allocation.

Ownership must be specified via `ownership_json` parameter with required fields: `ownership_type` (`"individual"`, `"joint"`, or `"beneficiary"`), `owner_ids` (list of person IDs), and optionally `beneficiary_id` (required for beneficiary type).

Allocation can optionally be specified via `allocation_json` with fields: `stocks_pct`, `bonds_pct`, and `cash_pct` (all integers 0-100 that sum to 100). If omitted, it defaults to 100% cash for cash-only account types (cash accounts, mortgage, real estate) and is required for every other type.

Optionally specify `tax_treatment` to include a tax profile in the response.

| Parameter                    | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `account_type`               | string | `"traditional_401k"`, `"roth_401k"`, `"traditional_ira"`, `"roth_ira"`, `"hsa"`, `"plan_529"`, `"taxable_brokerage"`, `"taxable_savings"`, `"taxable_checking"`, `"mortgage"`, `"real_estate"`, etc.                                                                                                                                                                                                                                                                                              |
| `balance_cents`              | int    | Current balance in cents                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `ownership_json`             | dict   | **Required.** Ownership structure as JSON. Must include: `ownership_type` (`"individual"`, `"joint"`, or `"beneficiary"`), `owner_ids` (list of person IDs), and optionally `beneficiary_id` (required for beneficiary type). Example: `{"ownership_type": "individual", "owner_ids": ["person-123"]}`                                                                                                                                                                                            |
| `allocation_json`            | dict   | Optional asset allocation as JSON. Must include: `stocks_pct`, `bonds_pct`, and `cash_pct` (all integers 0-100 that sum to 100). Example: `{"stocks_pct": 60, "bonds_pct": 30, "cash_pct": 10}`. If omitted, defaults to 100% cash for cash-only types (cash accounts, mortgage, real estate); required for every other type.                                                                                                                                                                     |
| `tax_treatment`              | string | `"pre_tax"`, `"post_tax_deferred"`, `"taxable"`, `"tax_advantaged"` (optional)                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `name`                       | string | Human-readable name (optional)                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `institution`                | string | Financial institution (optional)                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `account_number_last4`       | string | Last 4 digits (optional)                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `is_current_employer`        | bool   | For 401k: current employer? (optional)                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `employer_match_json`        | dict   | Employer matching configuration. Only valid on a current-employer 401k (`account_type` is `traditional_401k`/`roth_401k` and `is_current_employer` is true); rejected otherwise. Must include `formula_type`. For `"tiered"` add `tiers`; for `"non_elective"` set `non_elective_pct`. Example: `{"formula_type": "basic_safe_harbor"}` (optional).                                                                                                                                               |
| `mortgage_terms_json`        | dict   | Loan terms for a `"mortgage"` account (required for that type, ignored otherwise). Must include: `original_principal_cents`, `interest_rate` (annual decimal), `term_months`, `origination_date` (ISO 8601), and `monthly_payment_cents` (principal + interest only). Optionally `is_fixed_rate` (default true).                                                                                                                                                                                  |
| `property_details_json`      | dict   | Property details for a `"real_estate"` account (required for that type, ignored otherwise). Must include: `property_type` (`"primary_residence"`, `"investment_property"`, `"vacation_home"`, or `"rental_property"`), `purchase_price_cents`, and `purchase_date` (ISO 8601). Optional: `estimated_value_cents`, `appreciation_rate`, `building_type`, `city`, `state`, `zip`, `linked_mortgage_account_id`.                                                                                     |
| `loan_terms_json`            | dict   | Loan terms for a non-mortgage liability account — `"credit_card"`, `"student_loan"`, `"auto_loan"`, `"personal_loan"`, or `"other_loan"` (required for those types, ignored otherwise). Must include: `apr` (annual decimal) and `minimum_payment_cents`. Optionally `term_months` (set for an amortizing installment loan; omit for revolving debt like a credit card).                                                                                                                          |
| `goal_id`                    | string | Optional Goal ID to earmark this account to. The goal's funded amount then derives from this account's balance (omitted from the output when unset).                                                                                                                                                                                                                                                                                                                                              |
| `monthly_contribution_cents` | int    | Optional explicit monthly contribution earmarked to this account, in cents. Set it when the honest per-account contribution is known (e.g. an IRA at its annual cap, a taxable account taking no new money) so `project_plan` honors it as a fixed monthly amount instead of splitting the household surplus by balance; the remaining surplus is split by balance across the accounts without a pin. Non-negative; omit for the balance-weighted split. Inert on liability/real-estate accounts. |

### list_account_types

Returns all valid `account_type` string values with short descriptions. Use this to discover the exact values accepted by `create_account`, `get_account_limits`, and `get_allowed_asset_classes_for_account`.

No parameters.

### get_allowed_asset_classes_for_account

Returns which asset classes (stocks/bonds/cash) an account type can hold.

| Parameter      | Type   | Description  |
| -------------- | ------ | ------------ |
| `account_type` | string | Account type |

### get_account_limits

Returns non-tax limits: FDIC insurance, RMD requirements, purchase limits, early withdrawal penalties.

| Parameter      | Type   | Description                                                                                                                                                     |
| -------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `account_type` | string | Account type                                                                                                                                                    |
| `birth_year`   | int    | Optional owner birth year; corrects RMD start age per SECURE 2.0 (72 if born before 1951, 73 for 1951-1959, 75 for 1960 or later). Omit for the default age 73. |
