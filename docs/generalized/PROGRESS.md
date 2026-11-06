# Progress log (generalized fuzzer)

## Open decisions (left blank on purpose; the owner fills them in during reviews)
- Venue: TBD
- Paper authorship and AI-use statement: TBD
- Anonymous artifact mirror: TBD
- Final paper title (working title in PLAN.md section 1): TBD
- LLM model and API key for the solver/overlay/triage LLM calls (Claude or Gemini): TBD; until then `manual` mode
- Extra machines for evaluation (this one has 4 cores, 13 GB free disk): TBD

## Blocked
- `cargo build` of DataFusion `main` was blocked by the previous session's permission settings; retry, else use the `datafusion` pip package.

## Bug packages ready (for the owner to file)
- (none yet)

## Session log

## 2026-11-06
- Done: plan v2 (`PLAN.md`): thesis (rule-directed fuzzing), novelty table against SQLancer++, ShQveL, Sedar,
  Mozi, DQP, QPG, WhiteFox, DBcover, HyLLfuzz, Argus, SQLxDiff, ARG; decisions D1-D12; tasks A1-A4, B1-B5,
  C1-C6, D1-D4, E1-E5, P1-P4; evaluation RQ1-RQ7 sized for 4 cores.
- Checked: pip wheels available (duckdb 2.1.0.dev nightly, datafusion 55, pyturso 0.8.3, chdb 4.4, polars,
  z3-solver); GitHub clones work (sqlite/sqlite mirror, tursodatabase/turso, sqlancer); sqlite.org and
  other download hosts are blocked; GitHub REST API is not available for unattached repos; Java + Maven present.
- PostgreSQL status (verified on master 6 Nov): 6 of the 9 reported bugs fixed (#19803 abda2a2, #19771 776df8a,
  statistics b0392c2, NOT IN b7eee09, #19768 e405a46, IGNORE NULLS 69b20fd); 5 of the fixes are the team's patches.
- Next: A4, A1, A2, then B1 (DuckDB to 95 %) and start the DuckDB campaign.


One dated entry per work session: done, measured numbers, next, questions for the owner.

## 2026-11-02 (previous session, before hand-off)
- Done: plan (PLAN.md), hand-off notes (HANDOFF.md), DuckDB executor (crash-isolated worker,
  transactions, optimizer-off plan variants, metamorphic checks), DuckDB schema and config.
- Measured: DuckDB nightly 2.1.0.dev runs the PostgreSQL grammar unchanged with poor validity
  (300 test cases / 992 statements; top errors: jsonb `?` operator 336, unnamed CREATE INDEX,
  SET LOCAL, EXPLAIN options, int4range, jsonb_* functions).
- Next: dialect overlay mechanism (G2) and DuckDB overlay to ≥95 % validity, then campaigns.
- Open: `cargo build` for DataFusion main was blocked in that session (see Blocked).
