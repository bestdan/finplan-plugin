# Portfolio Tools

Capital market assumptions, portfolio characteristics, and glide path generation.

<!-- BEGIN GENERATED: tool-index portfolio -->

## Tool index

| Tool                                        | Description                                                                                                 | Parameters                                                           |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `calculate_portfolio_characteristics`       | Calculate expected return and volatility for a portfolio allocation.                                        | stocks_pct, bonds_pct, cash_pct, assumption_preset?                  |
| `calculate_portfolio_characteristics_batch` | Batch calculate_portfolio_characteristics: expected return and volatility for many allocations in one call. | allocations[{stocks_pct, bonds_pct, cash_pct, ...}]                  |
| `create_portfolio_assumptions`              | Create capital market assumptions (returns + volatility per asset class) from a preset.                     | preset?, stocks_return?, bonds_return?, cash_return?                 |
| `generate_glide_path`                       | Generate a glide path transitioning between two allocations over time.                                      | start_stocks_pct, start_bonds_pct, start_cash_pct, end_*, num_years? |

<!-- END GENERATED: tool-index portfolio -->

## Tools

### calculate_portfolio_characteristics

Allocations must sum to 100.

### calculate_portfolio_characteristics_batch

Use this instead of N serial calls when sizing several candidate mixes. Each `allocations` entry is a `calculate_portfolio_characteristics` parameter object (at minimum `{stocks_pct, bonds_pct, cash_pct}`). Results come back **in the same order** as the input. A malformed entry yields a per-entry `{success: false, error, message}` in its slot without failing the others. Up to 50 allocations per call.

### generate_glide_path

Start and end allocations must each sum to 100. `num_years` (default 30) is ignored when `age_based=True`.

When `age_based=True`, `current_age` is required and the tool models a target-date fund glidepath in three phases. The `start_*` fields are the young allocation and the `end_*` fields the retirement allocation. Defaults: `death_age` 95, `retirement_age` 67, `glide_start_age` 47.

1. Pre-glide (before `glide_start_age`): constant start allocation
2. Glide (`glide_start_age` to `retirement_age`): linear interpolation
3. Post-retirement (`retirement_age` to `death_age`): constant end allocation
