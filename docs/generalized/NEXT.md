# Hand-over for the next session (branch `generalized`, updated 13 Nov 2026)

Read `CLAUDE.md` first (commit identity v28k, no AI mentions in commits or files, the owner files
all bugs). Work on branch `generalized` (`generalised-improved` was merged into it on 13 Nov and deleted). Tests: `cd src && python -m pytest -q` (205 pass).

## What this branch adds over `generalized`

| New | Where | State |
|---|---|---|
| **Rule kernels**: for each optimizer rule that fires, the query is reduced on its derivation tree while the rule still fires (a minimal trigger learned from behaviour only) | `src/pgfuzz/rules/kernels.py`, `pgfuzz kernels CONFIG -n N --out DIR` | works; median 260 -> 57 tokens on SQLite |
| **Kernel composition + composition oracle**: two kernels joined by templates whose result follows from the parts (cross join = |A|*|B|, union = |A|+|B|, exists, CTE used twice, ...) | `TEMPLATES` in `kernels.py` | works; written as seeds with `-- pgfuzz:check kernel:<t>` |
| **Identity grafts**: kernel B planted inside a base table of kernel A under an always-true filter; A's full result must not change | `GRAFTS`, `graft()` | works |
| **State-restoration oracle**: after a rolled-back test case the tables and row counts must be as before; a leak is reported as check `state_restore` and the worker is reset | `Driver.state_fingerprint`, `WorkerExecutor._check_state` in `targets/base.py` | works; found Turso T-06 |
| Turso `main` target | `src/configs/turso_main.yaml`, `scripts/build_turso_main.sh` | config ready; wheel build was running when the session ended |
| `latestbugs/` | repo root | README with validated status; no bug ready to file yet |

Novelty check done (see PROGRESS.md): closest work is the SQL Server rule-testing framework
(SIGMOD 2009; needs rule patterns exported by the optimizer) and ARG (ASE 2025; single rules,
from rewriter source). Kernels learned by reduction, kernel composition with a built-in
oracle, and grafts were not found in prior work.

## Results so far (be honest in the paper)

- Kernels: SQLite 16 kernels / 9 of 30 rules; DuckDB and DataFusion mined (25 of 47 DataFusion rules).
  1,239 composed seeds on three engines: **no oracle violation** at default settings.
- Turso 0.8.3: T-06 (transaction lost after a runtime error) and T-07 (correlated subquery in
  HAVING) are real but **already fixed on main 0c9fe0dd9**: not filable.
- DuckDB "4 vs 5 rows" candidate: flaky (GROUP BY on a float aggregate). Consider excluding
  float aggregates as grouping keys from the determinism filter (`eval/differential.py: eligible`).

## Done on 12 Nov 2026

1. Hunt on newest code (Turso main via `configs/turso_main.yaml`, DuckDB nightly, DataFusion 55):
   every candidate triaged; verdicts in `latestbugs/README.md`. New: **T-08** (Turso, ready to
   file, `latestbugs/T-08-*`). The rest were known, already reported, or fixed on main.
2. Kernel seeds in campaigns: `configs/sqlite_kernels.yaml`, `configs/duckdb_kernels.yaml`
   (two arms: plain grammar vs. grammar + composed kernel seeds); corpora in `src/corpus/kernels/`.
3. The 11 Nov lead (Turso panic) became T-08.
4. Kernels from engine test suites: `pgfuzz kernels CFG --from-suite DIR` (SQLite: Turso's
   SQLite-compatible sqltests; DuckDB: `test/optimizer`, `test/sql/optimizer`).
5. Kernel transfer: `pgfuzz kernels CFG --transfer-from kernels.json` (result: correspondence,
   no new rules reached).
Tool fixes found on the way: DuckDB rule probe replaced a test case's own `disabled_optimizers`
(every rule looked as if it fired); probe harness stopped at the first failing setup statement
and could leave DuckDB in an aborted transaction; triage crashed on non-PostgreSQL wrong results;
known bugs can now match on SQL (`sql_regex`), so filed bugs stop flooding Turso campaigns.

## To do, in this order

1. File T-08 (owner; prompt and text in `latestbugs/T-08-*/issue.md`), then DF-02.
2. RQ8 for the paper: repeat `configs/{sqlite,duckdb,datafusion}_kernels.yaml` with 5 trials x 1 h
   and add "rule pairs per test case" (throughput-neutral) to `scripts/eval/kernels_rq8.py`.
   First results (3 x 15 min): `docs/generalized/results/rq8_kernels_2026-11-12.md`.
3. DataFusion suite kernels: run each probe in a worker process (a DataFusion test exhausts memory
   and Rust aborts the in-process miner); grammar-only DataFusion kernels are in the corpus.
4. More targets (chDB, Polars), the full evaluation (`scripts/eval/run_all.sh`), the paper.
5. Re-check the open upstream items weekly: Turso #11595, DataFusion #27236, DuckDB #28552
   (auto-merge on), PostgreSQL BUG #19826 v4, #19793, MCV patch.
