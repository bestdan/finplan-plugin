# Portfolio Tools

Capital market assumptions, portfolio characteristics, and glide path generation.

## Tools

### calculate_portfolio_characteristics

Calculate expected return and volatility for an allocation.

| Parameter                | Type   | Description                                                           |
| ------------------------ | ------ | --------------------------------------------------------------------- |
| `stocks_pct`             | int    | Stock allocation 0-100                                                |
| `bonds_pct`              | int    | Bond allocation 0-100                                                 |
| `cash_pct`               | int    | Cash allocation 0-100                                                 |
| `crypto_pct`             | int    | Crypto allocation 0-100 (default: 0)                                  |
| `real_estate_pct`        | int    | Real estate allocation 0-100 (default: 0)                             |
| `other_pct`              | int    | Other-asset allocation 0-100 (default: 0)                             |
| `assumption_preset`      | string | `"standard"`, `"conservative"`, or `"optimistic"` (default: standard) |
| `stocks_return`          | float  | Override stock return (optional)                                      |
| `stocks_volatility`      | float  | Override stock volatility (optional)                                  |
| `bonds_return`           | float  | Override bond return (optional)                                       |
| `bonds_volatility`       | float  | Override bond volatility (optional)                                   |
| `cash_return`            | float  | Override cash return (optional)                                       |
| `cash_volatility`        | float  | Override cash volatility (optional)                                   |
| `crypto_return`          | float  | Override crypto expected return (optional)                            |
| `crypto_volatility`      | float  | Override crypto volatility (optional)                                 |
| `real_estate_return`     | float  | Override real estate expected return (optional)                       |
| `real_estate_volatility` | float  | Override real estate volatility (optional)                            |
| `other_return`           | float  | Override other-asset expected return (optional)                       |
| `other_volatility`       | float  | Override other-asset volatility (optional)                            |

Allocations must sum to 100. Returns: `expected_annual_return`, `annual_volatility`.

### calculate_portfolio_characteristics_batch

Batch/vectorized `calculate_portfolio_characteristics`: evaluate many allocations in **one call**. Use this instead of N serial calls when sizing several candidate mixes (e.g. for a dashboard).

| Parameter     | Type       | Description                                                                                                                                                                                 |
| ------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `allocations` | list[dict] | List of allocations to evaluate. Each entry is a `calculate_portfolio_characteristics` parameter object — at minimum `{stocks_pct, bonds_pct, cash_pct}` plus any optional preset/override. |

**Response**: `{success, count, succeeded, failed, allocations}`. `allocations` holds one result per input entry, **in the same order**; each successful element has the same shape the single tool returns. A malformed entry yields a per-entry `{success: false, error, message}` in its slot without failing the others. Up to 50 allocations per call.

### generate_glide_path

Transition between two allocations over time. Supports both linear and age-based modes.

| Parameter               | Type | Description                                                                                |
| ----------------------- | ---- | ------------------------------------------------------------------------------------------ |
| `start_stocks_pct`      | int  | Starting stock allocation 0-100 (young allocation when age_based=True)                     |
| `start_bonds_pct`       | int  | Starting bond allocation 0-100 (young allocation when age_based=True)                      |
| `start_cash_pct`        | int  | Starting cash allocation 0-100 (young allocation when age_based=True)                      |
| `end_stocks_pct`        | int  | Ending stock allocation 0-100 (retirement allocation when age_based=True)                  |
| `end_bonds_pct`         | int  | Ending bond allocation 0-100 (retirement allocation when age_based=True)                   |
| `end_cash_pct`          | int  | Ending cash allocation 0-100 (retirement allocation when age_based=True)                   |
| `start_crypto_pct`      | int  | Starting crypto allocation 0-100, default 0 (young allocation when age_based=True)         |
| `start_real_estate_pct` | int  | Starting real estate allocation 0-100, default 0 (young allocation when age_based=True)    |
| `start_other_pct`       | int  | Starting other-asset allocation 0-100, default 0 (young allocation when age_based=True)    |
| `end_crypto_pct`        | int  | Ending crypto allocation 0-100, default 0 (retirement allocation when age_based=True)      |
| `end_real_estate_pct`   | int  | Ending real estate allocation 0-100, default 0 (retirement allocation when age_based=True) |
| `end_other_pct`         | int  | Ending other-asset allocation 0-100, default 0 (retirement allocation when age_based=True) |
| `num_years`             | int  | Years for the glide path (default: 30, ignored when age_based=True)                        |
| `sample_interval_years` | int  | Show allocation every N years (default: 5)                                                 |
| `age_based`             | bool | If True, use age-based 3-phase glide path instead of linear (default: false)               |
| `current_age`           | int  | Person's current age (required if age_based=True)                                          |
| `death_age`             | int  | Assumed age at death (default: 95, used if age_based=True)                                 |
| `retirement_age`        | int  | Retirement age (default: 67, used if age_based=True)                                       |
| `glide_start_age`       | int  | Age when allocation starts shifting (default: 47, used if age_based=True)                  |

Start and end allocations must each sum to 100.

When `age_based=True`, models a target-date fund glidepath with three phases:

1. Pre-glide (before `glide_start_age`): constant start allocation
2. Glide (`glide_start_age` to `retirement_age`): linear interpolation
3. Post-retirement (`retirement_age` to `death_age`): constant end allocation

### create_portfolio_assumptions

Create assumptions from a preset with optional per-asset-class overrides.

| Parameter                | Type   | Description                                                           |
| ------------------------ | ------ | --------------------------------------------------------------------- |
| `preset`                 | string | `"standard"`, `"conservative"`, or `"optimistic"` (default: standard) |
| `stocks_return`          | float  | Override stock expected return (optional)                             |
| `stocks_volatility`      | float  | Override stock volatility (optional)                                  |
| `bonds_return`           | float  | Override bond expected return (optional)                              |
| `bonds_volatility`       | float  | Override bond volatility (optional)                                   |
| `cash_return`            | float  | Override cash expected return (optional)                              |
| `cash_volatility`        | float  | Override cash volatility (optional)                                   |
| `crypto_return`          | float  | Override crypto expected annual return (optional)                     |
| `crypto_volatility`      | float  | Override crypto annual volatility (optional)                          |
| `real_estate_return`     | float  | Override real estate expected annual return (optional)                |
| `real_estate_volatility` | float  | Override real estate annual volatility (optional)                     |
| `other_return`           | float  | Override other-asset expected annual return (optional)                |
| `other_volatility`       | float  | Override other-asset annual volatility (optional)                     |

Returns: portfolio assumptions object with per-asset-class return and volatility.
