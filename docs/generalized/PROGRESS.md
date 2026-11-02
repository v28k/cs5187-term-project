# Progress log (generalized fuzzer)

## Open decisions (left blank on purpose; the owner fills them in during reviews)
- Venue: TBD
- Paper authorship and AI-use statement: TBD
- Anonymous artifact mirror: TBD

## Blocked
- `cargo build` of DataFusion `main` was blocked by the previous session's permission settings; retry, else use the `datafusion` pip package.

## Bug packages ready (for the owner to file)
- (none yet)

## Session log

One dated entry per work session: done, measured numbers, next, questions for the owner.

## 2026-11-02 (previous session, before hand-off)
- Done: plan (PLAN.md), hand-off notes (HANDOFF.md), DuckDB executor (crash-isolated worker,
  transactions, optimizer-off plan variants, metamorphic checks), DuckDB schema and config.
- Measured: DuckDB nightly 2.1.0.dev runs the PostgreSQL grammar unchanged with poor validity
  (300 test cases / 992 statements; top errors: jsonb `?` operator 336, unnamed CREATE INDEX,
  SET LOCAL, EXPLAIN options, int4range, jsonb_* functions).
- Next: dialect overlay mechanism (G2) and DuckDB overlay to ≥95 % validity, then campaigns.
- Open: `cargo build` for DataFusion main was blocked in that session (see Blocked).
