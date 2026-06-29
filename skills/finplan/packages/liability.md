# Liability Tools

Debt paydown projection for non-mortgage liabilities (credit cards, student / auto / personal / other loans). For mortgages, use [mortgage.md](mortgage.md).

## Tools

### project_liability_payoff

Project a liability's month-by-month balance and find its payoff date. Each month accrues interest at APR/12, applies the payment (plus any extra), and floors the balance at 0. A payment at or below the monthly interest never pays the debt down — the balance grows and `payoff_month` is null.

| Parameter               | Type  | Description                                                                               |
| ----------------------- | ----- | ----------------------------------------------------------------------------------------- |
| `balance_cents`         | int   | Current outstanding balance in cents, positive magnitude (234099 = $2,340.99)             |
| `annual_interest_rate`  | float | APR as a decimal between 0 and 1 (0.2499 = 24.99%)                                        |
| `monthly_payment_cents` | int   | Scheduled / minimum monthly payment in cents (7500 = $75)                                 |
| `months`                | int   | Number of months to project the balance forward                                           |
| `extra_payment_cents`   | int   | Optional extra principal paid each month, in cents (default 0) — pays the debt off sooner |
| `term_months`           | int   | Optional revolving-vs-installment label; echoed back, does not affect the payoff math     |

Returns file URLs + compact inline summary. The inline summary contains the payoff month, payoff years, start/end balances, and the payment breakdown. The full month-by-month trajectory is in the data file.

## File-based responses

```
result = project_liability_payoff(
    balance_cents=2_340_99,
    annual_interest_rate=0.2499,
    monthly_payment_cents=75_00,
    months=120,
    extra_payment_cents=50_00,
)

# result["urls"]["data"] -> full month-by-month balance trajectory
# result["urls"]["schema"] -> data structure description with jq examples
# result["summary"] -> payoff_month, payoff_years, start/end balance, payment breakdown
```

See [file-tools.md](file-tools.md) for details on file-based responses.

## Notes

- For mortgages, use `generate_mortgage_amortization_schedule` instead.
- All money in **cents**.
- Rates as **float decimals** (0.2499, not 24.99).
- `payoff_month` is null when the payment never retires the debt within `months` (e.g. a minimum payment below the monthly interest, where the balance grows).
