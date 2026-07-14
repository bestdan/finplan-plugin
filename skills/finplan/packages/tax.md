# Tax Tools

US federal income tax, capital gains calculations, after-tax projection adjustments, and resident state/local income tax.

## Tools

### calculate_federal_income_tax

Calculate federal income tax for given income and filing status. Includes marginal rate, effective rate, LTCG rate, and explanation.

| Parameter              | Type   | Description                                                                                      |
| ---------------------- | ------ | ------------------------------------------------------------------------------------------------ |
| `taxable_income_cents` | int    | Taxable income in cents                                                                          |
| `filing_status`        | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, `"qualifying_widow"` |
| `tax_year`             | int    | Tax year (default: `2026`)                                                                       |

Returns: `tax_owed_cents`, `tax_owed_dollars`, `marginal_rate`, `effective_rate`, `marginal_rate_percent`, `effective_rate_percent`, `ltcg_rate`, `ltcg_rate_percent`, `explanation`.

### calculate_capital_gains_tax_rate

Get the long-term capital gains tax rate for an income level.

| Parameter              | Type   | Description                |
| ---------------------- | ------ | -------------------------- |
| `taxable_income_cents` | int    | Taxable income in cents    |
| `filing_status`        | string | Same options as above      |
| `tax_year`             | int    | Tax year (default: `2026`) |

Returns: `ltcg_rate` (float, e.g., 0.15 = 15%).

### calculate_state_and_local_income_tax

Calculate resident state and (optionally) local income tax using full progressive brackets. Returns `success: false` with a message identifying the unsupported field when a state/locality/year combination has no implementation.

| Parameter                    | Type   | Description                                                                                         |
| ---------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| `state_code`                 | string | Two-letter US state code                                                                            |
| `state_taxable_income_cents` | int    | State taxable income in cents (after state deductions)                                              |
| `filing_status`              | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"` |
| `locality`                   | string | Optional resident locality slug. Leave empty for state-only.                                        |
| `tax_year`                   | int    | Tax year (default: `2026`)                                                                          |

Returns: `success`, `state_tax_cents`, `state_marginal_rate`, `state_effective_rate`, `state_standard_deduction_cents`, `local_tax_cents`, `total_state_and_local_tax_cents`, `combined_effective_rate`, `explanation`.

### calculate_federal_tax_liability

Calculate the full federal tax liability for a single year — AGI, deductions, taxable income, ordinary-bracket tax, preferential-rate (LTCG/qualified-dividend) stacking, NIIT, Additional Medicare, and AMT — composing the underlying primitives. When the filer itemizes, the deductible SALT amount is automatically added back as an AMT exclusion preference.

| Parameter                                  | Type   | Description                                                                                                                                              |
| ------------------------------------------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `filing_status`                            | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"`                                                      |
| `wages_cents`                              | int    | Regular W-2 wages in cents (default `0`; must exclude RSU/NQSO supplemental compensation)                                                                |
| `supplemental_ordinary_fica_subject_cents` | int    | RSU vest / NQSO exercise ordinary income, FICA-subject, in cents (default `0`)                                                                           |
| `supplemental_ordinary_fica_exempt_cents`  | int    | ISO disqualifying-disposition ordinary-income portion, FICA-exempt, in cents (default `0`)                                                               |
| `qualified_dividends_cents`                | int    | Qualified dividends in cents — subset of `ordinary_dividends_cents` (default `0`)                                                                        |
| `ordinary_dividends_cents`                 | int    | Total ordinary dividends (1099-DIV Box 1a) in cents (default `0`)                                                                                        |
| `short_term_capital_gains_cents`           | int    | Short-term capital gains in cents (default `0`)                                                                                                          |
| `long_term_capital_gains_cents`            | int    | Long-term capital gains in cents (default `0`)                                                                                                           |
| `interest_income_cents`                    | int    | Taxable interest income in cents (default `0`)                                                                                                           |
| `other_ordinary_cents`                     | int    | Other ordinary income in cents (default `0`)                                                                                                             |
| `above_the_line_adjustments_cents`         | int    | Above-the-line adjustments (401(k), HSA, SE tax/2, etc.) in cents (default `0`)                                                                          |
| `salt_paid_state_cents`                    | int    | State income tax paid in cents (default `0`)                                                                                                             |
| `salt_paid_local_cents`                    | int    | Local income tax paid in cents (default `0`)                                                                                                             |
| `salt_paid_property_cents`                 | int    | Property tax paid in cents (default `0`)                                                                                                                 |
| `mortgage_interest_cents`                  | int    | Home mortgage interest in cents (default `0`)                                                                                                            |
| `mortgage_principal_balance_cents`         | int    | Average mortgage principal balance in cents (default `0`)                                                                                                |
| `mortgage_origination_year`                | int    | Mortgage origination year — pre-2018 gets the $1M grandfathered cap; 2018+ gets $750K. Required when `mortgage_interest_cents > 0`; ignored otherwise.   |
| `charitable_cash_cents`                    | int    | Charitable cash contributions in cents (subject to the IRC §170 AGI ceiling, default `0`)                                                                |
| `charitable_appreciated_asset_cents`       | int    | Charitable gifts of appreciated long-term capital-gain property in cents (lower §170 ceiling, default `0`)                                               |
| `charitable_other_property_cents`          | int    | Charitable gifts of other (non-cash, non-appreciated) property in cents (default `0`)                                                                    |
| `medical_expenses_cents`                   | int    | Unreimbursed medical/dental expenses in cents; only the portion above 7.5% of AGI is deductible (IRC §213(a), default `0`)                               |
| `casualty_theft_loss_cents`                | int    | Casualty/theft loss in cents from a single federally declared disaster event; deductible only when `federally_declared_disaster` is `true` (default `0`) |
| `federally_declared_disaster`              | bool   | Set `true` for `casualty_theft_loss_cents` to be deductible post-TCJA (default `false`)                                                                  |
| `iso_preference_cents`                     | int    | ISO exercise-and-hold bargain element in cents (AMT deferral preference, default `0`)                                                                    |
| `tax_year`                                 | int    | Tax year, `2026` only (default: `2026`)                                                                                                                  |

Returns: `agi_cents`/`_dollars`, `magi_niit_cents`/`_dollars`, `deduction_taken_cents`/`_dollars`, `deduction_choice`, `taxable_income_cents`/`_dollars`, `ordinary_bracket_tax_cents`/`_dollars`, `preferential_rate_tax_cents`/`_dollars`, `niit_cents`/`_dollars`, `additional_medicare_cents`/`_dollars`, `amt_owed_cents`/`_dollars`, `amt_credit_carryforward_cents`/`_dollars`, `total_federal_liability_cents`/`_dollars`, `marginal_ordinary_rate`, `effective_rate`, `explanation`.

### calculate_amt

Calculate the Alternative Minimum Tax (Form 6251): AMTI, the phased-out exemption, the 26%/28% tentative minimum tax, AMT owed, and the Form 8801 minimum-tax-credit carryforward. Preference items split into deferral items (e.g. the ISO exercise-and-hold spread), which generate a recoverable credit, and exclusion items (e.g. the SALT add-back), which do not.

| Parameter                           | Type   | Description                                                                                         |
| ----------------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| `regular_taxable_income_cents`      | int    | Regular taxable income in cents                                                                     |
| `regular_tax_cents`                 | int    | Regular federal income tax (the AMT comparison baseline) in cents                                   |
| `filing_status`                     | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"` |
| `iso_exercise_spread_cents`         | int    | ISO exercise-and-hold spread in cents (deferral preference, default `0`)                            |
| `other_deferral_preferences_cents`  | int    | Other deferral (timing) preference items in cents (default `0`)                                     |
| `salt_addback_cents`                | int    | State and local tax add-back in cents (exclusion preference, default `0`)                           |
| `other_exclusion_preferences_cents` | int    | Other exclusion (permanent) preference items in cents (default `0`)                                 |
| `tax_year`                          | int    | Tax year (default: `2026`)                                                                          |

Returns: `amti_cents`, `exemption_cents`, `amt_base_cents`, `tentative_minimum_tax_cents`, `regular_tax_cents`, `amt_owed_cents`, `minimum_tax_credit_carryforward_cents`, `explanation`.

### model_iso_exercise

Model the tax effect of an incentive stock option (ISO) exercise. Returns the AMT preference (for the exercise-and-hold path) or ordinary income (for a same-year disqualifying disposition; FICA-exempt), in both `_cents` and `_dollars` form, plus share-surrender placeholders for the cashless / net-exercise scenario.

| Parameter                     | Type   | Description                                                                                                                   |
| ----------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `strike_cents`                | int    | Per-share strike (exercise) price in cents                                                                                    |
| `fmv_cents`                   | int    | Per-share fair market value at exercise, in cents                                                                             |
| `shares`                      | int    | Number of options exercised                                                                                                   |
| `intent`                      | string | `"hold"` (exercise-and-hold → AMT preference) or `"disqualify_same_year"` (same-year sale → ordinary income, FICA-exempt)     |
| `filing_status`               | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"`                           |
| `ytd_supplemental_paid_cents` | int    | Year-to-date supplemental wages already paid before this event in cents — unused for ISO, accepted for symmetry (default `0`) |
| `tax_year`                    | int    | Tax year, `2026` only (default: `2026`)                                                                                       |

Returns: `intent`, `shares`, `strike_cents`/`_dollars`, `fmv_cents`/`_dollars`, `ordinary_income_fica_subject_cents`/`_dollars`, `ordinary_income_fica_exempt_cents`/`_dollars`, `amt_preference_cents`/`_dollars`, `short_term_capital_gain_cents`/`_dollars`, `long_term_capital_gain_cents`/`_dollars`, `supplemental_withholding_cents`/`_dollars`, `shares_surrendered_for_strike`, `shares_surrendered_for_tax`, `shares_retained`, `explanation`.

### model_nqso_exercise

Model the tax effect of a non-qualified stock option (NQSO) exercise. Returns the bargain element ((FMV − strike) × shares) as FICA-subject ordinary (W-2) income, the mandatory federal supplemental-wage withholding (flat 22% up to the $1M aggregate YTD cap, mandatory 37% above), and zero AMT preference — in both `_cents` and `_dollars` form, plus a plain-English explanation.

| Parameter                     | Type   | Description                                                                                                                      |
| ----------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `strike_cents`                | int    | Per-share strike (exercise) price in cents                                                                                       |
| `fmv_cents`                   | int    | Per-share fair market value at exercise, in cents                                                                                |
| `shares`                      | int    | Number of options exercised                                                                                                      |
| `filing_status`               | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"`                              |
| `ytd_supplemental_paid_cents` | int    | Year-to-date supplemental wages already paid before this event in cents — positions the spread against the $1M cap (default `0`) |
| `tax_year`                    | int    | Tax year, `2026` only (default: `2026`)                                                                                          |

Returns: `shares`, `strike_cents`/`_dollars`, `fmv_cents`/`_dollars`, `ordinary_income_fica_subject_cents`/`_dollars`, `ordinary_income_fica_exempt_cents`/`_dollars`, `amt_preference_cents`/`_dollars`, `short_term_capital_gain_cents`/`_dollars`, `long_term_capital_gain_cents`/`_dollars`, `supplemental_withholding_cents`/`_dollars`, `shares_surrendered_for_strike`, `shares_surrendered_for_tax`, `shares_retained`, `explanation`.

### model_rsu_vest

Model the tax effect of a restricted stock unit (RSU) vest. Returns the vest value (FMV × shares_vesting) as FICA-subject ordinary (W-2) income, the mandatory federal supplemental-wage withholding (flat 22% up to the $1M aggregate YTD cap, mandatory 37% above), and zero AMT preference — in both `_cents` and `_dollars` form, plus a plain-English explanation.

| Parameter                     | Type   | Description                                                                                                                          |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `fmv_cents`                   | int    | Per-share fair market value at vest, in cents                                                                                        |
| `shares_vesting`              | int    | Number of shares vesting                                                                                                             |
| `filing_status`               | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"`                                  |
| `ytd_supplemental_paid_cents` | int    | Year-to-date supplemental wages already paid before this event in cents — positions the vest value against the $1M cap (default `0`) |
| `tax_year`                    | int    | Tax year, `2026` only (default: `2026`)                                                                                              |

Returns: `shares_vesting`, `fmv_cents`/`_dollars`, `ordinary_income_fica_subject_cents`/`_dollars`, `ordinary_income_fica_exempt_cents`/`_dollars`, `amt_preference_cents`/`_dollars`, `short_term_capital_gain_cents`/`_dollars`, `long_term_capital_gain_cents`/`_dollars`, `supplemental_withholding_cents`/`_dollars`, `shares_surrendered_for_strike`, `shares_surrendered_for_tax`, `shares_retained`, `explanation`.

### estimate_underpayment_safe_harbor

Estimate whether withholding meets the IRS safe-harbor threshold for avoiding underpayment penalties (IRC §6654(d)). Returns the safe-harbor target, the basis used (90% of current-year tax or 100/110% of prior-year tax), whether a penalty would apply, and suggested quarterly 1040-ES payments to close any gap.

| Parameter                          | Type   | Description                                                                                         |
| ---------------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| `prior_year_total_tax_cents`       | int    | Total tax from the prior year's return, in cents                                                    |
| `prior_year_agi_cents`             | int    | Adjusted gross income from the prior year's return, in cents                                        |
| `current_year_projected_tax_cents` | int    | Projected total federal tax for the current year, in cents                                          |
| `withholding_cents`                | int    | Year-to-date plus expected remaining withholding for the current year, in cents                     |
| `filing_status`                    | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"` |
| `tax_year`                         | int    | Current tax year (default: `2026`)                                                                  |

Returns: `safe_harbor_target_cents`/`_dollars`, `safe_harbor_basis`, `withholding_gap_cents`/`_dollars`, `penalty_applies`, `suggested_quarterly_payment_cents`/`_dollars`, `quarterly_due_dates`, `explanation`.

### get_tax_parameters

Look up year- and filing-status-specific federal tax scalars from the canonical registry: SALT cap and phase-down (OBBBA-modified), AMT exemption / phase-out / rate breakpoint, NIIT and Additional Medicare thresholds, supplemental wage withholding rates, mortgage acquisition-debt caps, and the 402(g) / 401(a)(17) / 414(v) / 415(c) retirement limits. Each scalar is returned in both `_cents` and `_dollars` form, plus a `source` citation string.

| Parameter       | Type   | Description                                                                                         |
| --------------- | ------ | --------------------------------------------------------------------------------------------------- |
| `filing_status` | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"` |
| `tax_year`      | int    | Tax year, `2026` only (default: `2026`)                                                             |

Returns: `salt_cap_cents`/`_dollars`, `salt_phaseout_threshold_cents`/`_dollars`, `salt_phaseout_rate`, `amt_exemption_cents`/`_dollars`, `amt_phaseout_threshold_cents`/`_dollars`, `amt_phaseout_rate`, `amt_rate_breakpoint_cents`/`_dollars`, `amt_lower_rate`, `amt_upper_rate`, `niit_threshold_cents`/`_dollars`, `niit_rate`, `additional_medicare_threshold_cents`/`_dollars`, `additional_medicare_rate`, `supplemental_wage_cap_cents`/`_dollars`, `supplemental_wage_rate_below_cap`, `supplemental_wage_rate_above_cap`, `mortgage_acquisition_debt_cap_post_tcja_cents`/`_dollars`, `mortgage_acquisition_debt_cap_grandfathered_cents`/`_dollars`, `elective_deferral_limit_cents`/`_dollars`, `compensation_limit_cents`/`_dollars`, `catchup_limit_cents`/`_dollars`, `total_annual_additions_limit_cents`/`_dollars`, `source`.

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

### analyze_roth_conversion

Analyze converting a traditional IRA/401(k) amount to Roth this year: the marginal federal tax cost of the conversion slice (two full-liability calls diffed, so bracket-stacking, NIIT, and AMT are captured), the resulting reduction in projected RMDs, and a convert-now vs leave-in-traditional break-even under an assumed future marginal rate. The conversion amount is given either explicitly (`conversion_amount_cents`) or by filling a target ordinary bracket (`fill_to_marginal_rate`) — provide exactly one. The break-even assumes the conversion tax is paid from the converted (IRA) funds. Provide `state_code` (with `state_taxable_income_base_cents`) to fold resident state+local income tax on the conversion into the cost and break-even; unsupported states return `success: false`. Out of scope: IRMAA tiers, ACA subsidy cliffs, multi-year conversion ladders.

| Parameter                                  | Type   | Description                                                                                                                                                                                                                                                             |
| ------------------------------------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `filing_status`                            | string | `"single"`, `"married_joint"`, `"married_separate"`, `"head_of_household"`, or `"qualifying_widow"`                                                                                                                                                                     |
| `traditional_balance_cents`                | int    | Traditional IRA/401(k) balance available to convert, in cents                                                                                                                                                                                                           |
| `birth_year`                               | int    | Account owner's birth year (for RMD projection)                                                                                                                                                                                                                         |
| `time_horizon_years`                       | int    | Years to project RMDs and terminal values                                                                                                                                                                                                                               |
| `future_marginal_rate`                     | float  | Assumed marginal ordinary rate at future withdrawal, as a decimal (0.30 = 30%)                                                                                                                                                                                          |
| `wages_cents`                              | int    | Regular W-2 wages in cents (default `0`; must exclude RSU/NQSO supplemental compensation)                                                                                                                                                                               |
| `supplemental_ordinary_fica_subject_cents` | int    | RSU vest / NQSO exercise ordinary income, FICA-subject, in cents (default `0`)                                                                                                                                                                                          |
| `supplemental_ordinary_fica_exempt_cents`  | int    | ISO disqualifying-disposition ordinary-income portion, FICA-exempt, in cents (default `0`)                                                                                                                                                                              |
| `qualified_dividends_cents`                | int    | Qualified dividends in cents — subset of `ordinary_dividends_cents` (default `0`)                                                                                                                                                                                       |
| `ordinary_dividends_cents`                 | int    | Total ordinary dividends (1099-DIV Box 1a) in cents (default `0`)                                                                                                                                                                                                       |
| `short_term_capital_gains_cents`           | int    | Short-term capital gains in cents (default `0`)                                                                                                                                                                                                                         |
| `long_term_capital_gains_cents`            | int    | Long-term capital gains in cents (default `0`)                                                                                                                                                                                                                          |
| `interest_income_cents`                    | int    | Taxable interest income in cents (default `0`)                                                                                                                                                                                                                          |
| `other_ordinary_cents`                     | int    | Other ordinary income in cents (default `0`)                                                                                                                                                                                                                            |
| `above_the_line_adjustments_cents`         | int    | Above-the-line adjustments (401(k), HSA, SE tax/2, etc.) in cents (default `0`)                                                                                                                                                                                         |
| `salt_paid_state_cents`                    | int    | State income tax paid in cents (default `0`)                                                                                                                                                                                                                            |
| `salt_paid_local_cents`                    | int    | Local income tax paid in cents (default `0`)                                                                                                                                                                                                                            |
| `salt_paid_property_cents`                 | int    | Property tax paid in cents (default `0`)                                                                                                                                                                                                                                |
| `mortgage_interest_cents`                  | int    | Home mortgage interest in cents (default `0`)                                                                                                                                                                                                                           |
| `mortgage_principal_balance_cents`         | int    | Average mortgage principal balance in cents (default `0`)                                                                                                                                                                                                               |
| `mortgage_origination_year`                | int    | Mortgage origination year — pre-2018 gets the $1M grandfathered cap; 2018+ gets $750K. Required when `mortgage_interest_cents > 0`; ignored otherwise.                                                                                                                  |
| `charitable_cash_cents`                    | int    | Charitable cash contributions in cents (subject to the IRC §170 AGI ceiling, default `0`)                                                                                                                                                                               |
| `charitable_appreciated_asset_cents`       | int    | Charitable gifts of appreciated long-term capital-gain property in cents (lower §170 ceiling, default `0`)                                                                                                                                                              |
| `charitable_other_property_cents`          | int    | Charitable gifts of other (non-cash, non-appreciated) property in cents (default `0`)                                                                                                                                                                                   |
| `medical_expenses_cents`                   | int    | Unreimbursed medical/dental expenses in cents; only the portion above 7.5% of AGI is deductible (IRC §213(a), default `0`)                                                                                                                                              |
| `casualty_theft_loss_cents`                | int    | Casualty/theft loss in cents from a single federally declared disaster event; deductible only when `federally_declared_disaster` is `true` (default `0`)                                                                                                                |
| `federally_declared_disaster`              | bool   | Set `true` for `casualty_theft_loss_cents` to be deductible post-TCJA (default `false`)                                                                                                                                                                                 |
| `iso_preference_cents`                     | int    | ISO exercise-and-hold bargain element in cents (AMT deferral preference, default `0`)                                                                                                                                                                                   |
| `expected_annual_return`                   | float  | Assumed nominal annual return as a decimal (default `0.06`)                                                                                                                                                                                                             |
| `conversion_amount_cents`                  | int    | Explicit conversion amount in cents. Provide this or `fill_to_marginal_rate`, not both (optional)                                                                                                                                                                       |
| `fill_to_marginal_rate`                    | float  | Fill-bracket mode: convert enough to raise ordinary taxable income to the top of the bracket with this marginal rate, e.g. `0.24` (optional)                                                                                                                            |
| `state_code`                               | string | Two-letter resident state code (e.g. `"NY"`). When set, resident state+local income tax on the conversion is folded into the cost and break-even; unsupported states return `success: false`. Omit for a federal-only analysis (optional)                               |
| `locality`                                 | string | Resident locality slug for local income tax (e.g. `"nyc"`, `"yonkers"`). Empty for state-only; ignored when `state_code` is omitted (default `""`)                                                                                                                      |
| `state_taxable_income_base_cents`          | int    | State taxable income before the conversion, in cents (after state deductions). Required when `state_code` is provided — it places the conversion slice in the state brackets (optional)                                                                                 |
| `future_state_marginal_rate`               | float  | Assumed resident state+local marginal rate at future withdrawal, as a decimal (e.g. `0.0685`). When `state_code` is set but this is omitted, the conversion's own state+local marginal cost rate is used as the proxy — state is then a wash in the decision (optional) |
| `tax_year`                                 | int    | Tax year, `2026` only (default: `2026`)                                                                                                                                                                                                                                 |

Returns: `assumptions` (echo of inputs, resolved `conversion_amount`, `conversion_mode`, `notes`, and — when `state_code` is set — a `state` block with the resident state/local assumptions and resolved future rates), `incremental_tax_cost_cents`/`_dollars` (federal), `early_withdrawal_penalty_cents`/`_dollars` (IRC §72(t) early-withdrawal penalty on the IRA funds used to pay the conversion tax when the owner is under 59½; `0` otherwise — folded into `break_even_future_rate`. Its base is the tax actually paid from the IRA: federal-only, or federal+state when `state_code` is set. The penalty is itself paid from the IRA and so penalizes itself, making the effective rate charged on that tax `0.10/0.90` ≈ 11.11%, not 10%), `marginal_cost_rate`, `baseline_marginal_ordinary_rate`, `post_conversion_marginal_ordinary_rate`, `rmd_reduction` (per-year `full_rmd`/`reduced_rmd`/`reduction`), `total_rmd_reduction_cents`/`_dollars`, `break_even` (`convert_now_terminal`, `leave_in_traditional_terminal`, `advantage`, `break_even_future_rate`, `recommendation`), `summary`. When `state_code` is set, also `state_incremental_tax_cost_cents`/`_dollars`, `state_marginal_cost_rate`, `combined_incremental_tax_cost_cents`/`_dollars`, and `combined_marginal_cost_rate` (federal+state); the `break_even` then reflects the combined cost plus any penalty.

## Usage notes

- All income in **cents**. 10000000 = $100,000.
- Filing status uses short strings: `"married_joint"` not `"married_filing_jointly"`.
- For after-tax projections: first run `run_projection`, then pass the result to `apply_after_tax_to_projection_result`.
