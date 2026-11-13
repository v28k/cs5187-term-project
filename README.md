# Arbor, generalized: rule-directed grammar fuzzing of SQL engines

CS-5187 term project A3, extended version. Team: **Venu Kummari, Bhuvan Chilukuti, Gowtham Reddy**
(IIT Guwahati). License: [MIT](LICENSE).

* **Course project (PostgreSQL fuzzer, paper, slides, submission package):** branch
  [`main`](https://github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi/tree/main).
* **This branch, `generalized`:** the same fuzzer (`pgfuzz`, called Arbor in the paper) extended to
  **DuckDB, SQLite, Turso and Apache DataFusion**, with new techniques and the bugs found with them.

## What this branch adds

| Technique | Where |
|---|---|
| One driver per engine in a crash-isolated worker process; a dialect overlay per engine on the same typed grammar, and an overlay miner that drafts the overlay from measured failure rates | `src/pgfuzz/targets/`, `src/grammar/overlays/`, `src/pgfuzz/grammar/miner.py` |
| Optimizer-rule firing (a rule fires if switching it off changes the plan) as feedback, coverage metric and localization signal, on release builds | `targets/*: fired`, `pgfuzz/grammar/generator.py` |
| Rule-targeted generation after coverage stalls | `pgfuzz/grammar/generator.py` |
| Z3 data synthesis for non-vacuous metamorphic checks | `src/pgfuzz/datasynth/` |
| Learned value normalizers for cross-engine differential testing | `src/pgfuzz/normalizers/`, `pgfuzz learn-normalizers` |
| Engine test suites as seeds | `pgfuzz import-tests` |
| **Rule kernels**: per rule, a query reduced while the rule still fires (also from the engines' own tests); **composition oracle** over pairs of kernels; **identity grafts**; **kernel transfer** across engines | `src/pgfuzz/rules/kernels.py`, `pgfuzz kernels` |
| **State-restoration oracle**: after a rolled-back test case every table has its old row count | `src/pgfuzz/targets/base.py` |
| Campaign -> triage -> filing package with a regression test in the engine's own format | `pgfuzz hunt`, `pgfuzz package`, `pgfuzz ledger` |

Design and evaluation plan: [`docs/generalized/DESIGN.md`](docs/generalized/DESIGN.md).
Remaining work: [`docs/generalized/FUTURE_WORK.md`](docs/generalized/FUTURE_WORK.md).

## Bugs

Filed upstream, each with a fix and a regression test (state on 13 Nov 2026):

| Engine | Bug | Issue | Pull request | State |
|---|---|---|---|---|
| Turso | `percentile_disc`/`percentile_cont` with an expression argument | [#11594](https://github.com/tursodatabase/turso/issues/11594) | [#11595](https://github.com/tursodatabase/turso/pull/11595) | open, in review |
| DuckDB | `min`/`max` over a nested value computed by a subquery (2.0.0 regression) | [#28551](https://github.com/duckdb/duckdb/issues/28551) | [#28552](https://github.com/duckdb/duckdb/pull/28552) | **approved** by a maintainer (auto-merge, 2.0 backport) |
| DataFusion | `UPDATE`/`DELETE` that repeat an expression fail on `__common_expr_1` | [#27235](https://github.com/apache/datafusion/issues/27235) | [#27236](https://github.com/apache/datafusion/pull/27236) | open, validated by a contributor |
| Turso | aggregate in `IN (SELECT ...)` next to a window function: wrong "misuse" error, or a panic | [#11796](https://github.com/tursodatabase/turso/issues/11796) | [#11797](https://github.com/tursodatabase/turso/pull/11797) | open |
| DataFusion | scalar subquery inside `VALUES`: internal error (DF-02) | filed 13 Nov 2026 | filed 13 Nov 2026 | open |

One command reproduces all five on the released versions the campaigns ran on (pyturso 0.8.3,
duckdb 2.0.0, datafusion 55.0.0, installed into `.venv-repro`; no build, no root, about a minute):

```sh
bash scripts/reproduce_generalized.sh
```

Output on 13 Nov 2026:

```
REPRODUCED      T-05   Turso #11594       percentile_disc/cont of an expression argument
REPRODUCED      T-08   Turso #11796       aggregate in an IN-subquery operand next to a window function
REPRODUCED      D-01   DuckDB #28551      min/max of a nested subquery: Cannot copy BoundSubqueryExpression
REPRODUCED      DF-01  DataFusion #27235  UPDATE with COALESCE: No field named __common_expr_1
REPRODUCED      DF-02  DataFusion DF-02   VALUES with a scalar subquery: internal error

Generalized bugs reproduced: 5 of 5
```

The PostgreSQL bugs (branch `main`) are reproduced by `sudo bash scripts/reproduce.sh` (10 of 10).

Found by the fuzzer but already fixed on the engine's development branch when we checked (not
filed): Turso T-01, T-02, T-06, T-07; DuckDB D-02; four DataFusion 55.0.0 bugs fixed on `main`.
Every package and every rejected candidate: [`docs/bughunt/`](docs/bughunt/) and
[`docs/bughunt/FINDINGS_2026-11.md`](docs/bughunt/FINDINGS_2026-11.md).

## Results so far

* Valid queries with the dialect overlays (600 test cases): DuckDB 96.3 %, SQLite 97.7 %, Turso 93.3 %,
  DataFusion 79.4 %. One mined overlay round alone: DuckDB statement validity 32.1 % -> 44.1 %.
* Learned normalizers: held-out DuckDB-vs-SQLite disagreements 28.7 % -> 3.6 %.
* Rule kernels in campaigns (3 trials x 15 min per arm): optimizer-rule pairs reached
  DataFusion 241 -> 276 and DuckDB 307 -> 386 (both also per test case), SQLite 86 -> 182 (there
  mostly because kernels run faster). Details: [`docs/generalized/results/`](docs/generalized/results/).

## Install and run

Python 3.10 or newer; pinned versions in [`src/requirements.txt`](src/requirements.txt).

```sh
cd src
pip install -r requirements.txt                      # includes duckdb, apsw, pyturso, datafusion, z3-solver
python -m pytest -q                                  # 205 unit tests
python -m pgfuzz -q sample configs/duckdb.yaml -n 300 --execute      # validity on DuckDB
python -m pgfuzz run configs/datafusion.yaml                          # one campaign (budget in the config)
python -m pgfuzz hunt configs/duckdb.yaml configs/datafusion.yaml --budget 600   # campaign + triage + packages
python -m pgfuzz kernels configs/duckdb.yaml -n 400 --out ../results/kernels/duckdb   # rule kernels
python -m pgfuzz run configs/duckdb_kernels.yaml -j 2                 # kernel experiment (two arms)
python3 ../scripts/eval/kernels_rq8.py results/duckdb_kernels         # its table
python -m pgfuzz ledger --root ../docs/bughunt                        # precision ledger and package states
```

Turso's development branch: `scripts/build_turso_main.sh` builds `pyturso` from source;
`configs/turso_main.yaml` uses it.

## Layout

| Path | Content |
|---|---|
| `src/` | the tool (`src/pgfuzz`), tests, grammar and overlays, configs, known-bug catalogs, kernel corpora |
| `scripts/` | builds, evaluation (`scripts/eval/`), baselines, benchmark and coverage scripts |
| `docs/generalized/` | design, future work, ledger, results, paper outline |
| `docs/bughunt/` | one package per bug (report, reproducer, fix, regression test, filing steps) |
| `paper/` | the paper: LaTeX source (`cd paper && make`) and the final PDF [`paper/paper.pdf`](paper/paper.pdf) |
| `runs/`, `triage/`, `docs/` (others) | the course project, as on `main` |
