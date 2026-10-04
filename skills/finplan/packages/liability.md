# Liability Tools

Debt paydown projection for non-mortgage liabilities (credit cards, student / auto / personal / other loans). For mortgages, use [mortgage.md](mortgage.md).

<!-- BEGIN GENERATED: tool-index liability -->

## Tool index

| Tool                       | Description                                                                | Parameters                                                                                             |
| -------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `project_liability_payoff` | Project a non-mortgage liability's month-by-month balance and payoff date. | balance_cents, annual_interest_rate, monthly_payment_cents, months, extra_payment_cents?, term_months? |

<!-- END GENERATED: tool-index liability -->

## Tools

### project_liability_payoff

Each month accrues interest at APR/12, applies the payment (plus any extra), and floors the balance at 0. A payment at or below the monthly interest never pays the debt down — the balance grows and `payoff_month` is null.

- `balance_cents` is a positive magnitude (234099 = $2,340.99).
- `extra_payment_cents` (default 0) is extra principal paid each month and pays the debt off sooner.
- `term_months` is an optional revolving-vs-installment label; it is echoed back and does not affect the payoff math.

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
