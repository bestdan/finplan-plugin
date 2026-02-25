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

Returns file URLs + compact inline summary. The inline summary contains total principal/interest and final balance. Full month-by-month schedule is in the data file.

## File-based responses

```
result = generate_mortgage_amortization_schedule(
    original_principal_cents=400_000_00,
    annual_interest_rate=0.0675,
    term_months=360,
    monthly_payment_cents=2_594_02,
)

# result["urls"]["data"] -> full schedule (month-by-month entries)
# result["urls"]["schema"] -> data structure description with jq examples
# result["summary"] -> total principal/interest, final balance
```

See [file-tools.md](file-tools.md) for details on file-based responses.

## Notes

- Payments are principal + interest only (no taxes, insurance, or PMI).
- All money in **cents**.
- Rates as **float decimals** (0.0675, not 6.75).
