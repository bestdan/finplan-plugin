# Account Tools

Financial account types, allocations, ownership, and creation.

## Tools

### create_account

Create a financial account with balance, ownership, and allocation.

Ownership must be specified via `ownership_json` parameter with required fields: `ownership_type` (`"individual"`, `"joint"`, or `"beneficiary"`), `owner_ids` (list of person IDs), and optionally `beneficiary_id` (required for beneficiary type).

Allocation can optionally be specified via `allocation_json` with fields: `stocks_pct`, `bonds_pct`, and `cash_pct` (all integers 0-100 that sum to 100). If omitted, defaults to 100% cash allocation.

Optionally specify `tax_treatment` to include a tax profile in the response.

| Parameter              | Type   | Description                                                                                                                                                                                                                                                                                            |
| ---------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `account_type`         | string | `"traditional_401k"`, `"roth_401k"`, `"traditional_ira"`, `"roth_ira"`, `"hsa"`, `"plan_529"`, `"taxable_brokerage"`, `"taxable_savings"`, `"taxable_checking"`, `"mortgage"`, `"real_estate"`, etc.                                                                                                   |
| `balance_cents`        | int    | Current balance in cents                                                                                                                                                                                                                                                                               |
| `ownership_json`       | dict   | **Required.** Ownership structure as JSON. Must include: `ownership_type` (`"individual"`, `"joint"`, or `"beneficiary"`), `owner_ids` (list of person IDs), and optionally `beneficiary_id` (required for beneficiary type). Example: `{"ownership_type": "individual", "owner_ids": ["person-123"]}` |
| `allocation_json`      | dict   | Optional asset allocation as JSON. Must include: `stocks_pct`, `bonds_pct`, and `cash_pct` (all integers 0-100 that sum to 100). Example: `{"stocks_pct": 60, "bonds_pct": 30, "cash_pct": 10}`. If omitted, defaults to 100% cash.                                                                    |
| `tax_treatment`        | string | `"pre_tax"`, `"post_tax_deferred"`, `"taxable"`, `"tax_advantaged"` (optional)                                                                                                                                                                                                                         |
| `name`                 | string | Human-readable name (optional)                                                                                                                                                                                                                                                                         |
| `institution`          | string | Financial institution (optional)                                                                                                                                                                                                                                                                       |
| `account_number_last4` | string | Last 4 digits (optional)                                                                                                                                                                                                                                                                               |
| `is_current_employer`  | bool   | For 401k: current employer? (optional)                                                                                                                                                                                                                                                                 |

### get_allowed_asset_classes_for_account

Returns which asset classes (stocks/bonds/cash) an account type can hold.

| Parameter      | Type   | Description  |
| -------------- | ------ | ------------ |
| `account_type` | string | Account type |

### get_account_limits

Returns non-tax limits: FDIC insurance, RMD requirements, purchase limits, early withdrawal penalties.

| Parameter      | Type   | Description  |
| -------------- | ------ | ------------ |
| `account_type` | string | Account type |
