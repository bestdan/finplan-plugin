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

**These tools are calculators; projections do not apply RMDs.** Neither `project_plan` nor `run_projection` forces a distribution from a pre-tax balance at the required beginning date, taxes it, or reinvests what is left — a pre-tax account compounds through the whole horizon. Call the tools below for the RMD figures; do not read them out of a projection.

## Tools

### calculate_required_minimum_distribution

`table_type` defaults to `"uniform_lifetime"`. `beneficiary_age` (spouse beneficiary's age at end of current year) is required for `"joint_life"` and rejected otherwise.

**Pick `"joint_life"` when the owner's sole beneficiary is a spouse more than 10 years younger.** The IRS Joint and Last Survivor Table then gives a longer distribution period — a smaller RMD — than the Uniform Lifetime Table. Owner 75 with a 60-year-old spouse divides by 28.3 instead of 24.6. A gap of 10 years or less is a validation error: the Uniform Lifetime Table already assumes a spouse exactly 10 years younger, so it is the right table there.

### calculate_rmd_shortfall_penalty

`penalty_rate` is the SECURE 2.0 rate: 0.25, or 0.10 when `corrected_within_two_years` is true (default false).

### project_rmd_schedule

Defaults: `years_to_project` 20, `annual_growth_rate` 0.05.

## Usage notes

- Roth 401(k) no longer requires RMDs as of 2024.
- IRAs can be aggregated (take total RMD from any combination); 401(k)s cannot.
