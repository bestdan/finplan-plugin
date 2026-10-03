# Mortgage Tools

Mortgage payment calculations and amortization schedules.

## Tools

### calculate_mortgage_monthly_payment

Fixed monthly P&I payment for a mortgage.

| Parameter              | Type  | Description                                   |
| ---------------------- | ----- | --------------------------------------------- |
| `principal_cents`      | int   | Loan principal in cents (40000000 = $400,000) |
| `annual_interest_rate` | float | Annual rate as decimal (0.0675 = 6.75%)       |
| `term_months`          | int   | Loan term in months (360 = 30 years)          |

Returns: `monthly_payment_cents`, `total_payments_cents`, `total_interest_cents`.

### generate_mortgage_amortization_schedule

Month-by-month schedule showing P&I split and declining balance.

| Parameter                  | Type  | Description                                           |
| -------------------------- | ----- | ----------------------------------------------------- |
| `original_principal_cents` | int   | Original loan amount in cents                         |
| `annual_interest_rate`     | float | Annual rate as decimal                                |
| `term_months`              | int   | Total loan term in months                             |
| `monthly_payment_cents`    | int   | Fixed monthly P&I payment in cents                    |
| `max_months`               | int   | Limit months generated (optional, default: full term) |

Returns file URLs + compact inline summary.

## Example

A $400,000, 30-year loan at 6.75% — `generate_mortgage_amortization_schedule` with these arguments, taking `monthly_payment_cents` from `calculate_mortgage_monthly_payment`:

```json
{
  "original_principal_cents": 40000000,
  "annual_interest_rate": 0.0675,
  "term_months": 360,
  "monthly_payment_cents": 259439
}
```

`summary` carries total principal, total interest, and the final balance; `urls.data` holds the month-by-month schedule and `urls.schema` its jq examples. See [file-tools.md](file-tools.md) for working with file-based responses.

## Notes

- Payments are principal + interest only (no taxes, insurance, or PMI).
- All money in **cents**.
- Rates as **float decimals** (0.0675, not 6.75).
