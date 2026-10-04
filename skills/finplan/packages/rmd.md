# RMD Tools

Required Minimum Distribution (RMD) calculations for retirement planning under SECURE 2.0 rules.

<!-- BEGIN GENERATED: tool-index rmd -->

## Tool index

| Tool                                      | Description                                                                           | Parameters                                                                              |
| ----------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `calculate_aggregated_ira_rmds`           | Calculate RMDs for multiple IRAs with aggregation (take from any one or combination). | ira_balances, age                                                                       |
| `calculate_required_minimum_distribution` | Calculate the Required Minimum Distribution for a single retirement account.          | prior_year_balance_cents, age, table_type?, beneficiary_age?                            |
| `calculate_rmd_shortfall_penalty`         | Calculate the penalty for failing to take the full RMD (25% or 10% if corrected).     | required_rmd_cents, actual_withdrawn_cents, corrected_within_two_years?                 |
| `check_rmd_required`                      | Check if RMDs are required for a specific tax year based on birth year.               | birth_year, tax_year                                                                    |
| `project_rmd_schedule`                    | Project future RMD requirements over multiple years with estimated account growth.    | birth_year, current_year, current_balance_cents, years_to_project?, annual_growth_rate? |

<!-- END GENERATED: tool-index rmd -->

## Tools

### calculate_required_minimum_distribution

`table_type` defaults to `"uniform_lifetime"`. `beneficiary_age` (spouse beneficiary's age at end of current year) is required for `"joint_life"` and rejected otherwise.

**Pick `"joint_life"` when the owner's sole beneficiary is a spouse more than 10 years younger.** The IRS Joint and Last Survivor Table then gives a longer distribution period — a smaller RMD — than the Uniform Lifetime Table. Owner 75 with a 60-year-old spouse divides by 28.3 instead of 24.6. A gap of 10 years or less is a validation error: the Uniform Lifetime Table already assumes a spouse exactly 10 years younger, so it is the right table there.

### calculate_rmd_shortfall_penalty

`penalty_rate` is 0.25, or 0.10 when `corrected_within_two_years` is true (default false).

### project_rmd_schedule

Defaults: `years_to_project` 20, `annual_growth_rate` 0.05.

## Usage notes

- All balances in **cents**. 50000000 = $500,000.
- Uses IRS Uniform Lifetime Table for account owners, the Joint and Last Survivor Table for an owner whose sole beneficiary is a spouse more than 10 years younger, and the Single Life Table for beneficiaries.
- SECURE 2.0 penalty rate: 25% of shortfall (reduced to 10% if corrected within 2 years).
- Roth 401(k) no longer requires RMDs as of 2024.
- IRAs can be aggregated (take total RMD from any combination); 401(k)s cannot.
