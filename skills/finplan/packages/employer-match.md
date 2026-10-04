# Employer Match Tools

401(k) employer matching formulas, vesting schedules, and match calculations.

<!-- BEGIN GENERATED: tool-index employer_match -->

## Tool index

| Tool                            | Description                                                                                                                     | Parameters                                                                                                                                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `calculate_401k_employer_match` | Calculate the employer match amount for a given employee contribution.                                                          | employer_match_json, employee_contribution_cents, annual_compensation_cents                                                                                                                           |
| `calculate_401k_vested_amount`  | Calculate the vested portion of employer contributions based on years of service.                                               | employer_match_json, total_employer_contributions_cents, years_of_service                                                                                                                             |
| `create_employer_match`         | Create an employer matching configuration for a 401(k) plan.                                                                    | formula_type, tiers?, vesting_type?, annual_match_cap_cents?                                                                                                                                          |
| `plan_401k_deferral`            | Plan the per-paycheck 401(k) deferral that reaches the year's limit, with catch-up, match captured, and early cap-out warnings. | tax_year, ytd_deferral_cents, remaining_pay_periods, per_period_gross_cents, employer_match_json?, birth_year?, age?, election_type?, proposed_election_cents?, proposed_election_pct?, account_type? |

<!-- END GENERATED: tool-index employer_match -->

## Tools

### create_employer_match

- `tiers` is `[{match_rate, up_to_deferral_pct}]`, for tiered/enhanced formulas.
- `non_elective_pct` is for `non_elective` (minimum 3% for safe harbor); `discretionary_pct` is the current discretionary match %.
- `cliff_years` (cliff vesting) is years until 100% vested, 1-7; `graded_schedule` is a year-to-percent mapping such as `{"1": 0, "2": 20, ...}`.
- `is_qaca` marks a QACA arrangement, which allows a 2-year cliff (default false). `true_up` is a year-end true-up (default false).

### calculate_401k_employer_match

`ytd_employer_match_cents` defaults to 0. `compensation_limit_cents` defaults to the 2026 IRS limit when omitted. `include_monthly=True` adds `monthly_employer_match_cents` (annual divided by 12); `include_max_match=True` adds `max_annual_match_cents`.

### plan_401k_deferral

Spreads what is left under the limit (with the age catch-up, including age 60-63) evenly across the remaining paychecks, with the rounding remainder on the final one. Use it when someone asks what per-paycheck election maxes out their 401(k).

- `tax_year` is 2024 or later. `ytd_deferral_cents` is deferrals already made this year across every 401(k)-family plan.
- `age` is age attained by December 31 of `tax_year` and overrides `birth_year`.
- `employer_match_json` is optional; it gives the match captured and, via `true_up`, the early-cap-out cost.
- `election_type` is `"flat"` (default) or `"percent"`; `account_type` is `"traditional_401k"` (default) or `"roth_401k"`.
- `warnings` cover early cap-out with no true-up and the match forfeited, below the full-match deferral rate, limit not yet published, and YTD over the limit.
