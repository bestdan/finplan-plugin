# Tax Tools

US federal income tax, capital gains calculations, and after-tax projection adjustments.

## Tools

### calculate_federal_income_tax

Calculate federal income tax for given income and filing status. Includes marginal rate, effective rate, LTCG rate, and explanation.

| Parameter              | Type   | Description                                                                |
| ---------------------- | ------ | -------------------------------------------------------------------------- |
| `taxable_income_cents` | int    | Taxable income in cents                                                    |
| `filing_status`        | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"` |
| `tax_year`             | int    | `2024` or `2025` (default: 2025)                                           |

Returns: `tax_owed_cents`, `tax_owed_dollars`, `marginal_rate`, `effective_rate`, `marginal_rate_percent`, `effective_rate_percent`, `ltcg_rate`, `ltcg_rate_percent`, `explanation`.

### calculate_capital_gains_tax_rate

Get the long-term capital gains tax rate (0%, 15%, or 20%) for an income level.

| Parameter              | Type   | Description                      |
| ---------------------- | ------ | -------------------------------- |
| `taxable_income_cents` | int    | Taxable income in cents          |
| `filing_status`        | string | Same options as above            |
| `tax_year`             | int    | `2024` or `2025` (default: 2025) |

Returns: `ltcg_rate` (float, e.g., 0.15 = 15%).

### apply_after_tax_to_projection_result

Apply withdrawal taxes to a projection result, computing after-tax spendable values by account type. Takes the output from `run_projection` and adjusts the `after_tax_percentiles` based on account-specific withdrawal tax rules.

| Parameter                  | Type   | Description                                                                                                    |
| -------------------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| `projection_result_json`   | dict   | ProjectionResult JSON from `run_projection`. Must contain `percentiles` dict.                                  |
| `account_tax_treatment`    | string | `"pre_tax"`, `"post_tax_deferred"`, `"taxable"`, or `"tax_advantaged"`                                         |
| `marginal_ordinary_rate`   | float  | Marginal ordinary income tax rate (0.22 = 22%)                                                                 |
| `ltcg_rate`                | float  | Long-term capital gains tax rate (0.15 = 15%)                                                                  |
| `taxable_income_type`      | string | `"none"` (default), `"ordinary_income"`, or `"investment_income"`                                              |
| `initial_cost_basis_cents` | int    | For taxable brokerage: original invested amount in cents. Cost basis is fixed; gain fraction grows. (optional) |

**Key behaviors by account type:**

- **pre_tax** (Traditional 401k/IRA): spendable = balance × (1 − marginal_rate)
- **post_tax_deferred** (Roth): spendable = balance (identity, no tax)
- **tax_advantaged** (HSA, 529): spendable = balance (identity for qualified expenses)
- **taxable** cash (savings, checking): spendable = balance (no withdrawal tax)
- **taxable** brokerage: spendable = balance − (gains × ltcg_rate)

Returns: `adjusted_result` (full ProjectionResult with corrected `after_tax_percentiles`), `summary`.

## Usage notes

- All income in **cents**. 10000000 = $100,000.
- Filing status uses short strings: `"married_joint"` not `"married_filing_jointly"`.
- Supported tax years: 2024, 2025.
- For after-tax projections: first run `run_projection`, then pass the result to `apply_after_tax_to_projection_result`.
