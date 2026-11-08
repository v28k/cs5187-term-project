# Progress log (generalized fuzzer)

## Open decisions (left blank on purpose; the owner fills them in during reviews)
- Venue: TBD
- Paper authorship and AI-use statement: TBD
- Anonymous artifact mirror: TBD
- Final paper title (working title in PLAN.md section 1): TBD
- LLM model and API key: only needed for Phase L (LLM extension, moved to the end by the owner): TBD
- Extra machines for evaluation (this one has 4 cores, 13 GB free disk): TBD

## Blocked
- `cargo build` of DataFusion `main` was blocked by the previous session's permission settings; retry, else use the `datafusion` pip package.
- Building SQLite trunk (`configure && make` from the GitHub mirror) was blocked by the permission classifier (7 Nov).
  Workaround: SQLite through APSW 3.54.1 (newest release); optimizer switches reached through the module's symbol table.
  Consequence: no trunk SQLite and no coverage build of SQLite (task C5) until building is allowed.
- Running a prebuilt Turso 0.9.0-pre CLI (GitHub release asset) was blocked (8 Nov), as is building Turso or
  DataFusion `main`. Consequence: Turso and DataFusion findings are reproduced only on the newest PyPI wheels
  (pyturso 0.8.3, datafusion-python 55.0.0); their packages say so and ask the owner to re-run on `main` first.
  **If the owner allows `cargo build` (DataFusion `datafusion-cli`, Turso `tursodb`), validation becomes automatic.**

## Bug packages ready (for the owner to file)
- `docs/bughunt/duckdb/D-01-minmax-nested-subquery/`: DuckDB 2.0.0 regression, `min`/`max` over a LIST/STRUCT/ARRAY
  value containing a subquery fails with "Cannot copy BoundSubqueryExpression" (from 2ef9f76b2e). Confidence: high
  (reproduced on 2.0.0 and nightly, works on 1.5.6; root cause in minmax.cpp). Issue text ready; no patch.
- `docs/bughunt/duckdb/D-02-outer-join-two-subqueries/`: DuckDB 2.0.0+ INTERNAL "Failed to bind column reference"
  for a LEFT/RIGHT JOIN or MERGE condition with two subqueries. Confidence: high (nightly, 2.0.0; 1.5.6 said
  "not implemented"). Issue text and sqllogictest ready.
- `docs/bughunt/datafusion/DF-01-update-coalesce-common-expr/`: `UPDATE t SET c0 = COALESCE(c0, 0)` (INT column)
  fails with "No field named __common_expr_1". Confidence: medium until re-run on `main` (steps.md).
- `docs/bughunt/datafusion/DF-02-values-scalar-subquery/`: `VALUES ((SELECT 1), 5)` -> internal error
  "ScalarSubqueryExpr evaluated before the subquery was executed". Confidence: medium until re-run on `main`.
- `docs/bughunt/turso/T-05-percentile-expression-argument/`: Turso percentile_disc/percentile_cont return NULL or
  "Percentile value must be between 0.0 and 1.0" when the value argument is an expression (wrong results vs SQLite).
  Confidence: medium-high (pyturso 0.8.3; re-run on main).
- `docs/bughunt/turso/T-02-window-arg-call-order-by-twice/`: Turso panic (unreachable!) for a window function over
  DATE()/DATETIME() referenced twice in ORDER BY. Confidence: medium (part of window.rs changed on main).
- `docs/bughunt/turso/T-01-full-join-rowid-equality/`: FULL JOIN on an INTEGER PRIMARY KEY rejected with "requires
  an equality condition". Confidence: medium (may be a known limitation).

## Session log

## 2026-11-07
- Done: A4 (workers die with their parent, run kills its process group), A1 (`pgfuzz/targets/base.py`: Driver +
  WorkerExecutor; DuckDB, SQLite, Turso drivers), A2 (overlay directives with cascading, element-level removal,
  type classes), dialect transforms (`x::T` to `CAST`), per-dialect literal/fill tables, `sample --execute` validity
  and error examples, generic CrossVersionExecutor (any engine pair).
- Measured validity (`sample --execute`, 600 test cases): DuckDB nightly 96.3 % of queries (from 24 % with the plain
  PostgreSQL grammar); SQLite 3.54.1 97.7 %; Turso 0.8.3 92.7 %.
- Rule switches verified: SQLite's 30 optimizer switches change plans exactly for the expected rule
  (QueryFlattener, SimplifyJoin, MinMaxOpt), first evidence for C1.
- Bugs: DuckDB D-01 packaged (see above). Lead T-01 (Turso): `FULL JOIN ... ON t.a = u.a` rejected with
  "requires an equality condition" when `u.a` is an INTEGER PRIMARY KEY; to check against Turso's docs/limits.
- Campaigns running: DuckDB nightly vs 2.0.0 (2 trials x 2 h), Turso vs SQLite (1 trial x 2 h).
- Decision: keep `postgres.pgg` as the base grammar ("core") and express every engine as overlays on it (the course
  project's grammar stays the single source); engine-specific features live in the overlays' second part.
- Next: triage campaign candidates; C1 rule-firing feedback; B4 DataFusion.

## 2026-11-06
- Done: plan v2 (`PLAN.md`): thesis (rule-directed fuzzing), novelty table against SQLancer++, ShQveL, Sedar,
  Mozi, DQP, QPG, WhiteFox, DBcover, HyLLfuzz, Argus, SQLxDiff, ARG; decisions D1-D12; tasks A1-A4, B1-B5,
  C1-C6, D1-D4, E1-E5, P1-P4; evaluation RQ1-RQ7 sized for 4 cores.
- Checked: pip wheels available (duckdb 2.1.0.dev nightly, datafusion 55, pyturso 0.8.3, chdb 4.4, polars,
  z3-solver); GitHub clones work (sqlite/sqlite mirror, tursodatabase/turso, sqlancer); sqlite.org and
  other download hosts are blocked; GitHub REST API is not available for unattached repos; Java + Maven present.
- PostgreSQL status (verified on master 6 Nov): 6 of the 9 reported bugs fixed (#19803 abda2a2, #19771 776df8a,
  statistics b0392c2, NOT IN b7eee09, #19768 e405a46, IGNORE NULLS 69b20fd); 5 of the fixes are the team's patches.
- Decision (owner, 6 Nov): the LLM extension comes last (Phase L in PLAN.md), after all other work;
  C2 is now rule-targeted generation without an LLM; C6 uses engine test suites as seeds.
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
