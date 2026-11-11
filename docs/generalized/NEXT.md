# Hand-over for the next session (branch `generalised-improved`, 11 Nov 2026)

Read `CLAUDE.md` first (commit identity v28k, no AI mentions in commits or files, the owner files
all bugs). Work on branch `generalised-improved`. Tests: `cd src && python -m pytest -q` (197 pass).

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

## To do, in this order

1. **Hunt on newest code only.** Finish `scripts/build_turso_main.sh`, then
   `python -m pgfuzz hunt configs/turso_main.yaml configs/duckdb.yaml configs/datafusion.yaml --budget 3600 --out ../results/hunt_main`.
   Re-check every candidate with `/root/arbor/turso-src/target/debug/tursodb` (or the engine's
   newest build) before packaging. DataFusion `main` needs datafusion-python built against it.
2. **Run kernel seeds inside campaigns** (rule ablation applies there): mine with
   `pgfuzz kernels configs/<engine>.yaml -n 600 --out ../results/kernels/<engine>`, then add
   `seeds: <that dir>/seeds` and `seed_prob: 0.2` to the generator params of a config copy.
3. **Unfinished hunt of 11 Nov**: `results/hunt_1111/` (campaign data only if the container
   survived). Open leads: Turso panic "aggregate called in scalar context"
   (`core/vdbe/execute.rs`), failure `3308362ffef6`; reduce with `pgfuzz triage` and check on main.
4. **Kernels for rules that never fire** (19 of 30 on SQLite): take them from the engines' own
   test suites (`pgfuzz import-tests`), probe each statement with `Lab.fired`, keep statements
   that fire a rule the grammar never fires, reduce with the token reducer.
5. **Kernel transfer across engines**: replay a kernel's tree under another engine's overlay and
   test whether an analogous rule fires.
6. More targets (chDB, Polars), evaluation runs, paper: `FUTURE_WORK.md`, `paper/OUTLINE.md`.
   Add an RQ: rule-pair coverage of composed kernels vs random generation (numbers are in
   `compose.json`: `pairs_tried`, `pairs_cofired`).
7. For every bug that still reproduces on the newest code: a folder in `latestbugs/<ID>/` with
   `issue.md` (exact title and text), `repro.sql`, expected vs actual output, versions checked;
   then tell the owner.
