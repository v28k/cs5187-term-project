# SQLite candidate ledger (precision ledger input; one line per signature)

| Signature | Oracle | Verdict | Notes |
|---|---|---|---|
| 5909f579a0b2 | metamorphic expr:plus_zero | false positive (dialect) | `d + 0` on a DATE column: dates are text in SQLite, so `'2024-01-02' + 0` is 2024; fixed: dialect data `rewrite_exclude: [date:plus_zero, tstz:plus_zero]` |
| 8b4d54361447 | metamorphic expr:plus_zero | false positive (dialect) | same class (date column + 0) |
