# Social Security Tools

Comprehensive SSA benefit estimation, claiming strategies, and earnings test.

## Tools

### estimate_social_security_pia_from_salary

Estimate Primary Insurance Amount from salary history.

| Parameter             | Type | Description                         |
| --------------------- | ---- | ----------------------------------- |
| `annual_salary_cents` | int  | Annual salary in cents              |
| `years_of_work`       | int  | Years working at this salary (1-45) |

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

| Parameter               | Type | Description                          |
| ----------------------- | ---- | ------------------------------------ |
| `pia_cents`             | int  | PIA in cents                         |
| `claiming_age_years`    | int  | Claiming age (62-70)                 |
| `life_expectancy_years` | int  | Expected age at death                |
| `birth_year`            | int  | Birth year                           |
| `claiming_age_months`   | int  | Additional months (0-11, default: 0) |

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
2. `estimate_social_security_benefits_all_ages` to see all claiming options
3. `estimate_social_security_breakeven_age` for claiming strategy
4. `calculate_social_security_lifetime_benefits` to compare total benefits at different ages
5. `estimate_social_security_spousal_benefit` if married
