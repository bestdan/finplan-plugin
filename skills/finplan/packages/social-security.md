# Social Security Tools

Comprehensive SSA benefit estimation, claiming strategies, and earnings test.

## Tools

### compare_social_security_claiming_ages

Composite claiming-age analysis in a single call: per-age monthly and lifetime benefits (nominal and today's dollars), pairwise breakeven ages, a life-expectancy sensitivity grid, the best claiming age per assumed lifespan, and optional household/survivor figures. A single age returns its full statistics; multiple ages add the pairwise breakevens. Prefer this over orchestrating the single-purpose tools below when the question is "when should I claim?".

| Parameter                   | Type      | Description                                                        |
| --------------------------- | --------- | ------------------------------------------------------------------ |
| `pia_cents`                 | int       | Primary Insurance Amount in cents                                  |
| `birth_year`                | int       | Birth year                                                         |
| `life_expectancy_years`     | int       | Assumed age at death (default: 85)                                 |
| `claiming_ages`             | list[int] | Whole-year ages to analyze, each 62-70 (default: 62, FRA, 70)      |
| `inflation`                 | float     | Annual inflation as decimal; COLA defaults to it (default: 0.0)    |
| `spouse_pia_cents`          | int       | Spouse's own PIA in cents; 0 = no own work record (default: 0)     |
| `spouse_birth_year`         | int       | Spouse's birth year; provide to include household/survivor figures |
| `spouse_claiming_age_years` | int       | Spouse's claiming age in whole years (default: spouse's FRA)       |

Returns: `assumptions` (echoes every default applied — re-call with one changed parameter for follow-ups), `by_claiming_age`, `breakevens`, `life_expectancy_sensitivity`, `best_claiming_age_at_assumed_life_expectancy`.

### calculate_social_security_pia_from_aime

Apply the SSA bend-point formula to an AIME you already have — from an SSA statement, from another tool, or computed by hand.

| Parameter    | Type | Description                                                                                          |
| ------------ | ---- | ---------------------------------------------------------------------------------------------------- |
| `aime_cents` | int  | Average Indexed Monthly Earnings in cents. An AIME, not an annual salary.                            |
| `year`       | int  | Calendar year whose bend points apply. Required — there is no default, so it is never silently 2026. |

Returns: `pia_cents`, `bend_points` (both bend points, so the three segments can be audited), `year`.

### estimate_social_security_pia_from_earnings_record

Estimate PIA in today's dollars from a year-by-year SSA earnings record. This tool takes a stop-work year but no claiming age — claiming age is applied downstream when converting the PIA to a benefit — so the pipeline can answer "I stop working at 63 but claim at 67", which `estimate_social_security_pia_from_salary` cannot express.

| Parameter                      | Type           | Description                                                                                                       |
| ------------------------------ | -------------- | ----------------------------------------------------------------------------------------------------------------- |
| `earnings_by_year`             | dict[int, int] | Social Security taxable earnings by calendar year, in cents. Not the uncapped Medicare wages column.              |
| `date_of_birth`                | str            | ISO date (YYYY-MM-DD). SSA deems attainment the day before the birthday, so a birth year cannot express it.       |
| `stop_work_year`               | int            | Last year worked, inclusive, at the full `future_annual_earnings_cents`. A partial final year goes in the record. |
| `future_annual_earnings_cents` | int            | Earnings for each year after the last recorded one through `stop_work_year`, in today's dollars.                  |

Returns: `pia_cents_today_dollars`, `if_worked_to_fra` (the work-to-FRA comparison, inline — no second call needed), `credits_earned`, `is_retirement_insured`, `top_35_years`, `eligibility_year`. Persists nothing.

### estimate_social_security_pia_from_salary

Estimate Primary Insurance Amount from salary history.

| Parameter             | Type | Description                                                                                            |
| --------------------- | ---- | ------------------------------------------------------------------------------------------------------ |
| `annual_salary_cents` | int  | Annual salary in cents                                                                                 |
| `years_of_work`       | int  | Years working at this salary (1-45)                                                                    |
| `year`                | int  | Year for SSA bend points and the wage-index (max taxable earnings) cap. Defaults to 2026 when omitted. |

Returns: `estimated_pia_cents` (monthly PIA).

### estimate_social_security_benefits_all_ages

Compare benefits at all claiming ages 62-70 in a single call.

| Parameter    | Type | Description                       |
| ------------ | ---- | --------------------------------- |
| `pia_cents`  | int  | Primary Insurance Amount in cents |
| `birth_year` | int  | Birth year                        |

Returns: `benefits_by_age` table with monthly/annual amounts and adjustment factors.

### estimate_social_security_breakeven_age

When total benefits from claiming at FRA equal claiming at 62. Living beyond this age makes waiting more beneficial.

| Parameter                   | Type | Description                                       |
| --------------------------- | ---- | ------------------------------------------------- |
| `pia_cents`                 | int  | Primary Insurance Amount in cents                 |
| `birth_year`                | int  | Birth year                                        |
| `early_claiming_age_years`  | int  | Early claiming age in years (default: 62)         |
| `early_claiming_age_months` | int  | Early claiming age additional months (default: 0) |
| `later_claiming_age_years`  | int  | Later claiming age in years (default: FRA)        |
| `later_claiming_age_months` | int  | Later claiming age additional months (default: 0) |

### calculate_social_security_lifetime_benefits

Total lifetime benefits from claiming age through life expectancy.

| Parameter               | Type  | Description                                                                                                                                                                                 |
| ----------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pia_cents`             | int   | PIA in cents                                                                                                                                                                                |
| `claiming_age_years`    | int   | Claiming age (62-70)                                                                                                                                                                        |
| `life_expectancy_years` | int   | Expected age at death                                                                                                                                                                       |
| `birth_year`            | int   | Birth year                                                                                                                                                                                  |
| `claiming_age_months`   | int   | Additional months (0-11, default: 0)                                                                                                                                                        |
| `inflation`             | float | Annual inflation rate as decimal (default: 0.0). When `inflation > 0`, COLA defaults to the inflation rate and `lifetime_benefits_real_cents`/`lifetime_benefits_real_dollars` are computed |
| `cola_rate`             | float | Annual COLA rate as decimal (default: None). Overrides the inflation-derived COLA, letting benefits grow at a rate independent of the inflation used for discounting                        |

### apply_social_security_earnings_test

Benefit reduction if working while receiving benefits before FRA.

| Parameter               | Type | Description                                   |
| ----------------------- | ---- | --------------------------------------------- |
| `annual_benefit_cents`  | int  | Annual Social Security benefit in cents       |
| `annual_earnings_cents` | int  | Annual earnings from work in cents            |
| `claiming_age_years`    | int  | Claiming age in years (62-70)                 |
| `birth_year`            | int  | Birth year                                    |
| `claiming_age_months`   | int  | Additional months (0-11, default: 0)          |
| `is_fra_year`           | bool | Whether this is the FRA year (default: false) |
| `year`                  | int  | Tax year (optional)                           |

### get_social_security_earnings_limit

Earnings limit for a specific year. Earnings above reduce benefits $1 per $2.

| Parameter             | Type | Description                                   |
| --------------------- | ---- | --------------------------------------------- |
| `claiming_age_years`  | int  | Claiming age in years (62-70)                 |
| `birth_year`          | int  | Birth year                                    |
| `claiming_age_months` | int  | Additional months (0-11, default: 0)          |
| `is_fra_year`         | bool | Whether this is the FRA year (default: false) |
| `year`                | int  | Tax year (optional)                           |

### estimate_social_security_spousal_benefit

Spousal benefit (up to 50% of worker's PIA at FRA, reduced for early claiming).

| Parameter             | Type | Description                            |
| --------------------- | ---- | -------------------------------------- |
| `worker_pia_cents`    | int  | Worker's PIA in cents                  |
| `claiming_age_years`  | int  | Spouse's claiming age (62-70)          |
| `birth_year`          | int  | Spouse's birth year                    |
| `own_pia_cents`       | int  | Spouse's own PIA in cents (default: 0) |
| `claiming_age_months` | int  | Additional months (0-11, default: 0)   |

### estimate_social_security_survivor_benefit

Survivor benefit (up to 100% of worker's benefit at FRA, claimable from age 60).

| Parameter                | Type | Description                               |
| ------------------------ | ---- | ----------------------------------------- |
| `deceased_benefit_cents` | int  | Deceased worker's benefit amount in cents |
| `claiming_age_years`     | int  | Survivor's claiming age (60-70)           |
| `birth_year`             | int  | Survivor's birth year                     |
| `own_pia_cents`          | int  | Survivor's own PIA in cents (default: 0)  |
| `claiming_age_months`    | int  | Additional months (0-11, default: 0)      |

## Typical workflow

1. `estimate_social_security_pia_from_salary` to get PIA from salary
2. `compare_social_security_claiming_ages` for full claiming-age analysis (benefits, breakevens, sensitivity, household figures) in one call
3. Single-purpose tools (`estimate_social_security_benefits_all_ages`, `estimate_social_security_breakeven_age`, `calculate_social_security_lifetime_benefits`, `estimate_social_security_spousal_benefit`) for month-precision claiming ages or to audit individual figures
