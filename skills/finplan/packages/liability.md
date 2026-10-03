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

Returns file URLs + compact inline summary.

## Example

A $2,340.99 card balance at 24.99% APR, paying $75/month plus $50 extra — `project_liability_payoff` with these arguments:

```json
{
  "balance_cents": 234099,
  "annual_interest_rate": 0.2499,
  "monthly_payment_cents": 7500,
  "months": 120,
  "extra_payment_cents": 5000
}
```

`summary` carries `payoff_month`, `payoff_years`, start/end balance, and the payment breakdown; `urls.data` holds the month-by-month trajectory and `urls.schema` its jq examples. See [file-tools.md](file-tools.md) for working with file-based responses.

## Notes

- For mortgages, use `generate_mortgage_amortization_schedule` instead.
- All money in **cents**.
- Rates as **float decimals** (0.2499, not 24.99).
- `payoff_month` is null when the payment never retires the debt within `months` (e.g. a minimum payment below the monthly interest, where the balance grows).
