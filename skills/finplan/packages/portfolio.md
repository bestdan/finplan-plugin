# Portfolio Tools

Capital market assumptions, portfolio characteristics, and glide path generation.

## Tools

### calculate_portfolio_characteristics

Calculate expected return and volatility for an allocation.

| Parameter           | Type   | Description                                                           |
| ------------------- | ------ | --------------------------------------------------------------------- |
| `stocks_pct`        | int    | Stock allocation 0-100                                                |
| `bonds_pct`         | int    | Bond allocation 0-100                                                 |
| `cash_pct`          | int    | Cash allocation 0-100                                                 |
| `assumption_preset` | string | `"standard"`, `"conservative"`, or `"optimistic"` (default: standard) |
| `stocks_return`     | float  | Override stock return (optional)                                      |
| `stocks_volatility` | float  | Override stock volatility (optional)                                  |
| `bonds_return`      | float  | Override bond return (optional)                                       |
| `bonds_volatility`  | float  | Override bond volatility (optional)                                   |
| `cash_return`       | float  | Override cash return (optional)                                       |
| `cash_volatility`   | float  | Override cash volatility (optional)                                   |

Allocations must sum to 100. Returns: `expected_annual_return`, `annual_volatility`.

### generate_glide_path

Transition between two allocations over time. Supports both linear and age-based modes.

| Parameter               | Type | Description                                                                  |
| ----------------------- | ---- | ---------------------------------------------------------------------------- |
| `start_stocks_pct`      | int  | Starting stock allocation 0-100 (young allocation when age_based=True)       |
| `start_bonds_pct`       | int  | Starting bond allocation 0-100 (young allocation when age_based=True)        |
| `start_cash_pct`        | int  | Starting cash allocation 0-100 (young allocation when age_based=True)        |
| `end_stocks_pct`        | int  | Ending stock allocation 0-100 (retirement allocation when age_based=True)    |
| `end_bonds_pct`         | int  | Ending bond allocation 0-100 (retirement allocation when age_based=True)     |
| `end_cash_pct`          | int  | Ending cash allocation 0-100 (retirement allocation when age_based=True)     |
| `num_years`             | int  | Years for the glide path (default: 30, ignored when age_based=True)          |
| `sample_interval_years` | int  | Show allocation every N years (default: 5)                                   |
| `age_based`             | bool | If True, use age-based 3-phase glide path instead of linear (default: false) |
| `current_age`           | int  | Person's current age (required if age_based=True)                            |
| `death_age`             | int  | Assumed age at death (default: 95, used if age_based=True)                   |
| `retirement_age`        | int  | Retirement age (default: 67, used if age_based=True)                         |
| `glide_start_age`       | int  | Age when allocation starts shifting (default: 47, used if age_based=True)    |

Start and end allocations must each sum to 100.

When `age_based=True`, models a target-date fund glidepath with three phases:

1. Pre-glide (before `glide_start_age`): constant start allocation
2. Glide (`glide_start_age` to `retirement_age`): linear interpolation
3. Post-retirement (`retirement_age` to `death_age`): constant end allocation

### create_portfolio_assumptions

Create assumptions from a preset with optional per-asset-class overrides.

| Parameter           | Type   | Description                                                           |
| ------------------- | ------ | --------------------------------------------------------------------- |
| `preset`            | string | `"standard"`, `"conservative"`, or `"optimistic"` (default: standard) |
| `stocks_return`     | float  | Override stock expected return (optional)                             |
| `stocks_volatility` | float  | Override stock volatility (optional)                                  |
| `bonds_return`      | float  | Override bond expected return (optional)                              |
| `bonds_volatility`  | float  | Override bond volatility (optional)                                   |
| `cash_return`       | float  | Override cash expected return (optional)                              |
| `cash_volatility`   | float  | Override cash volatility (optional)                                   |

Returns: portfolio assumptions object with per-asset-class return and volatility.
