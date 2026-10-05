# Social Security Tools

Comprehensive SSA benefit estimation, claiming strategies, and earnings test.

<!-- BEGIN GENERATED: tool-index social_security -->

## Tool index

| Tool                                                | Description                                                                                                                                                                                                    | Parameters                                                                                                                                   |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `apply_social_security_earnings_test`               | Apply the Social Security earnings test to determine benefit reduction while working.                                                                                                                          | annual_benefit_cents, annual_earnings_cents, claiming_age_years, birth_year, claiming_age_months?, is_fra_year?, year?                       |
| `calculate_social_security_lifetime_benefits`       | Calculate total lifetime Social Security benefits for break-even analysis.                                                                                                                                     | pia_cents, claiming_age_years, life_expectancy_years, birth_year, claiming_age_months?, inflation?, cola_rate?                               |
| `calculate_social_security_pia_from_aime`           | Calculate PIA from Average Indexed Monthly Earnings using a year's SSA bend points.                                                                                                                            | aime_cents, year                                                                                                                             |
| `compare_social_security_claiming_ages`             | Analyze one or more Social Security claiming ages in one call: monthly and lifetime benefits per age, pairwise breakeven ages, life-expectancy sensitivity, best age, and optional household/survivor figures. | pia_cents, birth_year, life_expectancy_years?, claiming_ages?, inflation?, spouse_pia_cents?, spouse_birth_year?, spouse_claiming_age_years? |
| `estimate_social_security_benefits_all_ages`        | Estimate Social Security benefits at all possible claiming ages (62-70).                                                                                                                                       | pia_cents, birth_year                                                                                                                        |
| `estimate_social_security_breakeven_age`            | Estimate the break-even age for comparing Social Security claiming strategies.                                                                                                                                 | pia_cents, birth_year, early_claiming_age_years?, early_claiming_age_months?, later_claiming_age_years?, later_claiming_age_months?          |
| `estimate_social_security_pia_from_earnings_record` | Estimate PIA in today's dollars from a year-by-year SSA earnings record. Answers what it costs to retire early, with the stop-work year independent of the claiming age.                                       | earnings_by_year, date_of_birth, stop_work_year, future_annual_earnings_cents                                                                |
| `estimate_social_security_pia_from_salary`          | Estimate PIA from one flat career salary. A fallback for when no earnings record is available: it models the same salary every year and cannot express a stop-work year.                                       | annual_salary_cents, years_of_work, year?                                                                                                    |
| `estimate_social_security_spousal_benefit`          | Estimate spousal Social Security benefit (up to 50% of worker's PIA at FRA).                                                                                                                                   | worker_pia_cents, claiming_age_years, birth_year, own_pia_cents?, claiming_age_months?                                                       |
| `estimate_social_security_survivor_benefit`         | Estimate survivor Social Security benefit (up to 100% of deceased worker's benefit).                                                                                                                           | deceased_benefit_cents, claiming_age_years, birth_year, own_pia_cents?, claiming_age_months?                                                 |
| `get_social_security_earnings_limit`                | Get the Social Security earnings limit for a given claiming age and year.                                                                                                                                      | claiming_age_years, birth_year, claiming_age_months?, is_fra_year?, year?                                                                    |

<!-- END GENERATED: tool-index social_security -->

## Tool notes

### compare_social_security_claiming_ages

Prefer this over orchestrating the single-purpose tools when the question is "when should I claim?". A single age returns its full statistics; multiple ages add the pairwise breakevens.

- Defaults: `life_expectancy_years` 85; `claiming_ages` are 62, FRA, 70 (whole years, each 62-70); `inflation` 0.0, and COLA defaults to it.
- `spouse_pia_cents` 0 means the spouse has no own work record. Provide `spouse_birth_year` to include household/survivor figures; `spouse_claiming_age_years` defaults to the spouse's FRA.
- The `assumptions` field echoes every default applied. Re-call with one changed parameter for follow-ups.

### calculate_social_security_pia_from_aime

Applies the bend-point formula to an AIME you already have. `aime_cents` is an AIME, not an annual salary. `year` is required: there is no default, so it is never silently 2026. The result includes both bend points so the three segments can be audited.

### estimate_social_security_pia_from_earnings_record

Takes a stop-work year but no claiming age; claiming age is applied downstream when converting the PIA to a benefit. That is what lets the pipeline answer "I stop working at 63 but claim at 67", which `estimate_social_security_pia_from_salary` cannot. Persists nothing.

- `earnings_by_year` is Social Security taxable earnings in cents, not the uncapped Medicare wages column.
- `date_of_birth` is an ISO date, not a birth year: SSA deems attainment the day before the birthday.
- `stop_work_year` is the last year worked, inclusive, at the full `future_annual_earnings_cents`. A partial final year goes in the record.
- `future_annual_earnings_cents` covers each year after the last recorded one through `stop_work_year`, in today's dollars.
- `if_worked_to_fra` in the result is the work-to-FRA comparison, so no second call is needed.

**Accuracy far from 62: surface `todays_dollars_note` to the user.** The PIA is in today's dollars, SSA's own statement basis: current earnings continue, no economy-wide wage growth. That basis is near-exact in the units the benefit formula is written in (wages) and drifts in the units a person spends (prices), and the drift grows with distance from age 62. The tool emits the quantified caveat itself once the caller is 10 or more years from 62, so pass `todays_dollars_note` through rather than paraphrasing it. **Do not compare `pia_cents_today_dollars` against a nominal, inflated projection elsewhere in a plan without accounting for this.**

### estimate_social_security_pia_from_salary

**Fallback for when no earnings record is available.** It assumes the same salary every year and **cannot express a stop-work year**; use `estimate_social_security_pia_from_earnings_record` if the caller has a real earnings record. `years_of_work` is 1-45. `year` sets the bend points and the wage-index (max taxable earnings) cap, and defaults to 2026 when omitted.

### calculate_social_security_lifetime_benefits

When `inflation > 0`, COLA defaults to the inflation rate and `lifetime_benefits_real_cents`/`lifetime_benefits_real_dollars` are computed. `cola_rate` overrides the inflation-derived COLA, letting benefits grow at a rate independent of the inflation used for discounting.

### Optional month and year parameters

`claiming_age_months` (0-11, default 0) refines the claiming age on the single-purpose tools. `estimate_social_security_breakeven_age` also takes `early_claiming_age_months` and `later_claiming_age_months` (default 0), with the early age defaulting to 62 and the later to FRA. `apply_social_security_earnings_test` and `get_social_security_earnings_limit` take `is_fra_year` (default false) and an optional `year`.

### estimate_social_security_spousal_benefit and estimate_social_security_survivor_benefit

`own_pia_cents` defaults to 0 on both. The spousal tool's `claiming_age_years` is 62-70; the survivor tool's is 60-70.

## Typical workflow

**Step 1 — get a PIA.** Three entry points, in order of how much the caller has:

1. `estimate_social_security_pia_from_earnings_record` — the default. Takes a year-by-year SSA earnings record and returns a PIA in today's dollars, plus the work-to-FRA comparison inline. This is the only tool that can express a stop-work year.
2. `calculate_social_security_pia_from_aime` — when the caller already has an AIME (an SSA statement reports one) and needs only the bend-point formula applied.
3. `estimate_social_security_pia_from_salary` — **fallback for when no earnings record is available.** It approximates a flat career at one salary and **cannot express a stop-work year**, so it cannot answer "what does stopping work at 63 cost me?". Prefer either tool above it whenever the caller has the inputs.

**Step 2 — turn the PIA into a claiming decision.**

4. `compare_social_security_claiming_ages` for full claiming-age analysis (benefits, breakevens, sensitivity, household figures) in one call
5. Single-purpose tools (`estimate_social_security_benefits_all_ages`, `estimate_social_security_breakeven_age`, `calculate_social_security_lifetime_benefits`, `estimate_social_security_spousal_benefit`) for month-precision claiming ages or to audit individual figures
