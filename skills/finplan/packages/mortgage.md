# Mortgage Tools

Mortgage payment calculations and amortization schedules.

<!-- BEGIN GENERATED: tool-index mortgage -->

## Tool index

| Tool                                      | Description                                                              | Parameters                                                                         |
| ----------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `calculate_mortgage_monthly_payment`      | Calculate the fixed monthly principal + interest payment for a mortgage. | principal_cents, annual_interest_rate, term_months                                 |
| `generate_mortgage_amortization_schedule` | Generate a month-by-month amortization schedule for a mortgage.          | original_principal_cents, annual_interest_rate, term_months, monthly_payment_cents |

<!-- END GENERATED: tool-index mortgage -->

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
- `max_months` (optional) limits the months generated; the default is the full term.
