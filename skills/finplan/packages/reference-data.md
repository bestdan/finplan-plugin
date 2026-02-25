# Reference Data

Static lookup data for FinPlan MCP tools. Embedded here to avoid unnecessary tool calls.

## Account Types

| Value                       | Description                                                           |
| --------------------------- | --------------------------------------------------------------------- |
| `traditional_401k`          | Employer-sponsored 401k with pre-tax contributions                    |
| `roth_401k`                 | Employer-sponsored 401k with post-tax contributions (tax-free growth) |
| `traditional_401k_rollover` | 401k rolled over from previous employer                               |
| `traditional_ira`           | Individual Retirement Account with pre-tax contributions              |
| `roth_ira`                  | Individual Retirement Account with post-tax contributions             |
| `sep_ira`                   | Simplified Employee Pension IRA (for self-employed/small business)    |
| `simple_ira`                | Savings Incentive Match Plan for Employees IRA                        |
| `hsa`                       | Health Savings Account (triple tax advantaged)                        |
| `fsa`                       | Flexible Spending Account (use-it-or-lose-it)                         |
| `plan_529`                  | Tax-advantaged education savings plan                                 |
| `taxable_brokerage`         | Standard taxable investment account                                   |
| `taxable_savings`           | Standard savings account (cash only)                                  |
| `taxable_checking`          | Checking account (cash only)                                          |
| `taxable_money_market`      | Money market account (cash/cash equivalents)                          |
| `taxable_cd`                | Certificate of Deposit (cash, fixed term)                             |
| `ibonds`                    | Series I Savings Bonds (inflation-protected, purchase limits)         |
| `crypto_exchange`           | Cryptocurrency exchange account                                       |
| `mortgage`                  | Mortgage loan (liability account, tracks outstanding principal)       |
| `real_estate`               | Real estate property (asset account, tracks property value)           |

## Property Types

| Value                 | Description                                                         |
| --------------------- | ------------------------------------------------------------------- |
| `primary_residence`   | Owner's primary home (qualifies for primary residence tax benefits) |
| `investment_property` | Investment property held for appreciation                           |
| `vacation_home`       | Second home used for personal vacation/recreation                   |
| `rental_property`     | Property held to generate rental income                             |

## Ownership Types

| Value         | Description                                                 |
| ------------- | ----------------------------------------------------------- |
| `individual`  | Account owned by a single person                            |
| `joint`       | Account owned jointly by multiple people (e.g., spouses)    |
| `beneficiary` | Account where person is a beneficiary (e.g., inherited IRA) |

## Asset Classes

| Value    | Description                                       |
| -------- | ------------------------------------------------- |
| `stocks` | Equity investments (stocks, stock funds)          |
| `bonds`  | Fixed income investments (bonds, bond funds)      |
| `cash`   | Cash and cash equivalents (money market, savings) |

## Account Tax Treatments

| Value               | Description                                                                                   |
| ------------------- | --------------------------------------------------------------------------------------------- |
| `pre_tax`           | Pre-tax contributions, tax-deferred growth, taxed withdrawals (Traditional 401k/IRA)          |
| `post_tax_deferred` | Post-tax contributions, tax-free growth, tax-free withdrawals (Roth 401k/IRA)                 |
| `taxable`           | After-tax contributions, capital gains on sales, dividends taxed annually (Taxable brokerage) |
| `tax_advantaged`    | Special tax advantages (HSA: triple tax advantaged, 529: tax-free growth for education)       |

## Projection Methods

| Value           | Description                                                                                |
| --------------- | ------------------------------------------------------------------------------------------ |
| `closed_form`   | Analytical Kan & Zhou projection with direct percentile computation (default, recommended) |
| `auto`          | Automatically select deterministic or Monte Carlo based on volatility                      |
| `deterministic` | Force deterministic projection (requires zero volatility)                                  |
| `monte_carlo`   | Force Monte Carlo simulation (works with any volatility)                                   |

Use `closed_form` for most cases. Use `monte_carlo` only for complex scenarios or to validate closed-form results.

## Portfolio Assumption Presets

| Preset         | Description                                                        | Stocks        | Bonds       | Cash          |
| -------------- | ------------------------------------------------------------------ | ------------- | ----------- | ------------- |
| `standard`     | Default assumptions based on typical long-term historical averages | 7% / 16% vol  | 4% / 6% vol | 2% / 1% vol   |
| `conservative` | Lower expected returns with higher volatility                      | 5% / 18% vol  | 3% / 7% vol | 1.5% / 1% vol |
| `optimistic`   | Higher expected returns                                            | 10% / 14% vol | 5% / 5% vol | 3% / 0.5% vol |

## Goal Types

`retirement`, `emergency_fund`, `major_purchase`, `education`, `annual_tax`, `debt_payoff`, `general_savings`, `charitable_giving`, `home_downpayment`, `vacation`, `wedding`, `business_startup`, `medical_expense`, `home_improvement`, `vehicle_purchase`, `custom`

## Goal Funding Strategies

| Value                | Description                                                                                                |
| -------------------- | ---------------------------------------------------------------------------------------------------------- |
| `fixed_contribution` | Fixed dollar amount each month (requires `contribution_amount_cents`)                                      |
| `percentage_income`  | Percentage of monthly income (requires `contribution_percentage`)                                          |
| `fill_to_target`     | Calculate required contribution to reach target by date (requires `target_amount_cents` and `target_date`) |
| `minimum_balance`    | Maintain a minimum balance at all times (requires `target_amount_cents`)                                   |
| `surplus_allocation` | Allocate any surplus funds after other obligations                                                         |

## 401(k) Match Formula Types

| Value                  | Description                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------- |
| `basic_safe_harbor`    | 100% of first 3% + 50% of next 2% = max 4% match. Immediate vesting required.      |
| `enhanced_safe_harbor` | At least as generous as basic, up to 6% deferral base. Immediate vesting required. |
| `non_elective`         | Fixed % of compensation regardless of deferral. Minimum 3% for safe harbor.        |
| `tiered`               | Custom matching tiers (e.g., 50% up to 6%). Vesting schedule varies.               |
| `discretionary`        | Employer-determined match, can vary year to year.                                  |

## Vesting Schedule Types

| Value       | Description                                                   |
| ----------- | ------------------------------------------------------------- |
| `immediate` | 100% vested when contributed. Required for safe harbor plans. |
| `cliff`     | 0% until cliff date, then 100%. Maximum 7 years per ERISA.    |
| `graded`    | Gradual vesting over time (e.g., 20% per year over 6 years).  |

## RMD Account Types

**Requires RMD:** `traditional_401k`, `traditional_401k_rollover`, `traditional_ira`, `sep_ira`, `simple_ira`

**No RMD Required:** `roth_401k` (changed in 2024 under SECURE 2.0), `roth_ira`, `hsa`, `plan_529`, `taxable_brokerage`

## SSA Limits by Year

| Year | FRA Earnings Limit | Under FRA Earnings Limit | COLA | Max Taxable Earnings | Bend Point 1 | Bend Point 2 |
| ---- | ------------------ | ------------------------ | ---- | -------------------- | ------------ | ------------ |
| 2024 | $59,520            | $22,320                  | 3.2% | $168,600             | $1,174       | $7,078       |
| 2025 | $62,160            | $23,400                  | 2.5% | $176,100             | $1,226       | $7,391       |
| 2026 | $63,780            | $24,120                  | 2.5% | $181,200             | $1,253       | $7,553       |

## Supported SSA Benefit Years

2024, 2025, 2026

## RMD Starting Ages (SECURE 2.0)

| Birth Year    | RMD Starting Age | Rule                    |
| ------------- | ---------------- | ----------------------- |
| Before 1951   | 72               | Legacy (pre-SECURE Act) |
| 1951-1959     | 73               | SECURE 2.0              |
| 1960 or later | 75               | SECURE 2.0              |
