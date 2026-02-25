# Employer Match Tools

401(k) employer matching formulas, vesting schedules, and match calculations.

## Tools

### create_employer_match

Create a complete employer match configuration.

| Parameter                | Type       | Description                                                                                      |
| ------------------------ | ---------- | ------------------------------------------------------------------------------------------------ |
| `formula_type`           | string     | `"basic_safe_harbor"`, `"enhanced_safe_harbor"`, `"non_elective"`, `"tiered"`, `"discretionary"` |
| `tiers`                  | list[dict] | Match tiers: `[{match_rate, up_to_deferral_pct}]` (for tiered/enhanced)                          |
| `non_elective_pct`       | float      | Contribution % (for non_elective, min 3% for safe harbor)                                        |
| `discretionary_pct`      | float      | Current discretionary match %                                                                    |
| `vesting_type`           | string     | `"immediate"`, `"cliff"`, `"graded"` (optional)                                                  |
| `cliff_years`            | int        | Years until 100% vested (for cliff, 1-7)                                                         |
| `graded_schedule`        | dict       | `{"1": 0, "2": 20, ...}` year-to-pct mapping                                                     |
| `annual_match_cap_cents` | int        | Annual cap on match in cents (optional)                                                          |
| `is_qaca`                | bool       | QACA arrangement (allows 2-yr cliff, default: false)                                             |
| `true_up`                | bool       | Year-end true-up (default: false)                                                                |

### calculate_401k_employer_match

Calculate match for a given employee contribution. Optionally includes monthly breakdown and/or maximum possible annual match.

| Parameter                     | Type | Description                                                                     |
| ----------------------------- | ---- | ------------------------------------------------------------------------------- |
| `employer_match_json`         | dict | Match config from `create_employer_match`                                       |
| `employee_contribution_cents` | int  | Employee deferral in cents                                                      |
| `annual_compensation_cents`   | int  | Annual compensation in cents                                                    |
| `ytd_employer_match_cents`    | int  | YTD match already contributed (default: 0)                                      |
| `include_monthly`             | bool | If True, also calculate monthly match by dividing annual by 12 (default: false) |
| `include_max_match`           | bool | If True, also calculate maximum possible annual employer match (default: false) |

Returns: `employer_match_cents`, `effective_deferral_pct`, `effective_match_pct`. When `include_monthly=True`, also returns `monthly_employer_match_cents`. When `include_max_match=True`, also returns `max_annual_match_cents`.

### calculate_401k_vested_amount

Vested portion of employer contributions based on years of service.

| Parameter                            | Type | Description                           |
| ------------------------------------ | ---- | ------------------------------------- |
| `employer_match_json`                | dict | Match config                          |
| `total_employer_contributions_cents` | int  | Total employer contributions in cents |
| `years_of_service`                   | int  | Years with employer                   |
