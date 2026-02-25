# RMD Tools

Required Minimum Distribution (RMD) calculations for retirement planning under SECURE 2.0 rules.

## Tools

### calculate_required_minimum_distribution

Calculate the Required Minimum Distribution for a retirement account using IRS life expectancy tables.

| Parameter                  | Type   | Description                                               |
| -------------------------- | ------ | --------------------------------------------------------- |
| `prior_year_balance_cents` | int    | Account balance as of December 31 of prior year, in cents |
| `age`                      | int    | Account owner's age at end of current year                |
| `table_type`               | string | `"uniform_lifetime"` (default) or `"single_life"`         |

Returns: `rmd_amount_cents`, `rmd_amount_dollars`, `distribution_period`, `explanation`.

### check_rmd_required

Check if RMDs are required for a specific tax year.

| Parameter    | Type | Description                |
| ------------ | ---- | -------------------------- |
| `birth_year` | int  | Account owner's birth year |
| `tax_year`   | int  | Tax year to check          |

Returns: `rmd_required` (boolean), `age_at_year_end`, `rmd_start_age`, `first_rmd_year`, `rule_applied`.

### calculate_rmd_shortfall_penalty

Calculate the penalty for failing to take the full RMD.

| Parameter                    | Type | Description                                             |
| ---------------------------- | ---- | ------------------------------------------------------- |
| `required_rmd_cents`         | int  | Required RMD amount in cents                            |
| `actual_withdrawn_cents`     | int  | Amount actually withdrawn in cents                      |
| `corrected_within_two_years` | bool | Whether shortfall was corrected timely (default: false) |

Returns: `shortfall_cents`, `penalty_cents`, `penalty_rate` (0.25 or 0.10 if corrected).

### project_rmd_schedule

Project future RMD requirements over multiple years.

| Parameter               | Type  | Description                                 |
| ----------------------- | ----- | ------------------------------------------- |
| `birth_year`            | int   | Account owner's birth year                  |
| `current_year`          | int   | Current tax year                            |
| `current_balance_cents` | int   | Current account balance in cents            |
| `years_to_project`      | int   | Number of years to project (default: 20)    |
| `annual_growth_rate`    | float | Expected annual growth rate (default: 0.05) |

Returns: `schedule` (list of yearly RMDs), `total_projected_rmd_cents`, `first_rmd_year`.

### calculate_aggregated_ira_rmds

Calculate RMDs for multiple IRAs with aggregation rules.

| Parameter      | Type | Description                                            |
| -------------- | ---- | ------------------------------------------------------ |
| `ira_balances` | list | List of `{"account_id": string, "balance_cents": int}` |
| `age`          | int  | Account owner's age at end of current year             |

Returns: `total_rmd_cents`, `account_rmds` (per-account breakdown), `can_aggregate`.

Note: IRA RMDs can be aggregated; 401(k) RMDs cannot.

## Usage notes

- All balances in **cents**. 50000000 = $500,000.
- Uses IRS Uniform Lifetime Table for account owners, Single Life Table for beneficiaries.
- SECURE 2.0 penalty rate: 25% of shortfall (reduced to 10% if corrected within 2 years).
- Roth 401(k) no longer requires RMDs as of 2024.
- IRAs can be aggregated (take total RMD from any combination); 401(k)s cannot.
