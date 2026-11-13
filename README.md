# Arbor: LLM-guided grammar-aware fuzzing of PostgreSQL

CS-5187 term project A3 (IIT Guwahati, 2026). Team: **Venu Kummari, Bhuvan Chilukuti, Gowtham Reddy**.
The tool is called `pgfuzz` in the code and **Arbor** in the paper. License: [MIT](LICENSE).
Repository: <https://github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi>. Branch `main` holds the course project (this README); branch
[`generalized`](https://github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi/tree/generalized) holds the generalized fuzzer.

Arbor generates SQL as typed derivation trees from a grammar of 78 rules (83 after the additions for the rediscovery runs), rewrites the trees into
metamorphic checks (TLP, NoREC, typed expression rewrites, a row-level-security check, a
cardinality-estimate check, plan-variant and cross-version oracles), detects crashes, assertion
failures, internal errors and hangs, reduces every finding on its tree and tokens, and extends the
grammar from recent PostgreSQL commits with an LLM behind a server-side validation gate.

* **Paper:** [`paper/paper.pdf`](paper/paper.pdf) (LaTeX source in [`paper-source/`](paper-source/)).
* **Other deliverables:** [`completion/`](completion/README.md) (slides, complete project guide,
  progress material, contributions, bug list).
* **Generalized fuzzer** (DuckDB, SQLite, Turso, DataFusion): branch
  [`generalized`](https://github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi/tree/generalized), summary in
  [`docs/generalized/README.md`](docs/generalized/README.md).
* **Further techniques after the course paper** (same branch
  [`generalized`](https://github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi/tree/generalized)):
  optimizer-rule *kernels* (minimal queries that trigger one rule, learned by reduction, also from
  the engines' own test suites), a composition oracle over pairs of kernels, identity grafts, a
  state-restoration oracle for rolled-back test cases, and cross-engine kernel transfer. In 15-minute
  campaigns, kernel seeds raised the optimizer-rule pairs reached on DataFusion from 241 to 276 and on
  DuckDB from 307 to 386 (both also per test case), and on SQLite from 86 to 182 (there mostly because
  kernels run faster);
  `docs/generalized/results/` on that branch.

## Headline result

Arbor found **ten PostgreSQL bugs** that we reported upstream: **eight are fixed upstream, six of
them with our patches**, and the other two are under review with our patches. One command reproduces
the fuzzer finding all ten in a 150-second run (section "One-command reproduction").

## Upstream bug reports and their state (13 Nov 2026)

| # | Bug | Upstream report | State |
|---|---|---|---|
| 1 | parallel `Append` assertion in `create_append_path` | [BUG #19803](https://postgr.es/m/19803-1fcc1df108c54ab6@postgresql.org) | **merged**: fixed in `abda2a2c` (David Rowley), back-patched to 14 |
| 2 | `to_char()` NUL byte with a trailing decimal point (breaks `NORMALIZE`) | [BUG #19771](https://www.postgresql.org/message-id/19771-4f173b891525020c@postgresql.org) | **merged**: our patch, `776df8a6`, committed by Tom Lane |
| 3 | duplicate statistics expression: assertion in `dependencies_clauselist_selectivity` | [pgsql-bugs thread](https://www.postgresql.org/message-id/PN0P287MB0903563C70D8E5B81912E855A7602@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, `b0392c26`, committed by David Rowley, back-patched to 14 |
| 4 | `JSON_TABLE` assigns no collations (wrong result in 17/18, assertion on master) | [BUG #19768](https://www.postgresql.org/message-id/19768-3633daa830be95db@postgresql.org) | **merged**: our patch, [`e405a46c`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=e405a46c45), committed by Amit Langote, back-patched to 17 |
| 5 | `NOT IN` anti-join ignores an implicit cast (wrong result on master) | [pgsql-bugs thread](https://www.postgresql.org/message-id/PN0P287MB090375874C6D5433282EC9DFA7642@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, [`b7eee09e`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=b7eee09eab), committed by Richard Guo |
| 6 | `first_value`/`nth_value` with `IGNORE NULLS` never returns (ignores cancel) | [pgsql-bugs thread](https://www.postgresql.org/message-id/PN0P287MB09038F3BD9921EBACF5646F6A7632@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, [`69b20fdd`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=69b20fdd20), committed by Tatsuo Ishii |
| 7 | `MERGE` into a partitioned table: "SubPlan found with no parent plan" | [BUG #19802](https://www.postgresql.org/message-id/19802-ef50a8f1a4b5deee@postgresql.org) | **merged**: fixed in `7a5559a6` (Tender Wang, committed by Dean Rasheed), back-patched to 15 |
| 8 | `range @> NULL` folded to a constant (wrong result in 17, 18, master) | [BUG #19793](https://www.postgresql.org/message-id/19793-16d3a1bf33dff0fb@postgresql.org) | **open**: reported with a patch |
| 9 | `pg_restore_extended_stats` accepts non-finite MCV frequencies | pgsql-hackers ([our patch](docs/bughunt/bhuvan/patches/0001-Reject-non-finite-MCV-frequencies-in-pg_restore_exte.patch)) | **open**: patch submitted |
| 10 | `corr()`/`regr_*()` of a constant input differ under partial aggregation | [BUG #19826](https://postgr.es/m/19826-4b769cb5342fdfe7@postgresql.org) | **merged**: our patch, [`ef1b7404`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=ef1b740441) committed by Tom Lane, back-patched to 19 |

Also: an independent reproducer for BUG #19766. Patch versions for BUG #19826 (v1 to v4):
`docs/bughunt/new/`. Reproducers and patches: [`docs/bughunt/`](docs/bughunt/).

Generalized fuzzer (branch `generalized`), each filed with a fix and a regression test:

| Engine | Bug | Issue | Pull request | State |
|---|---|---|---|---|
| Turso | `percentile_disc`/`percentile_cont` with an expression argument | [#11594](https://github.com/tursodatabase/turso/issues/11594) | [#11595](https://github.com/tursodatabase/turso/pull/11595) | **open** (in review; test for a case found by a reviewer added 12 Nov) |
| DuckDB | `min`/`max` over a nested value computed by a subquery (2.0.0 regression) | [#28551](https://github.com/duckdb/duckdb/issues/28551) | [#28552](https://github.com/duckdb/duckdb/pull/28552) | **approved**: auto-merge enabled by a DuckDB maintainer, marked for the 2.0 backport |
| DataFusion | `UPDATE`/`DELETE` that repeat an expression fail on `__common_expr_1` | [#27235](https://github.com/apache/datafusion/issues/27235) | [#27236](https://github.com/apache/datafusion/pull/27236) | **open** (validated by a contributor, awaiting a committer) |
| Turso | aggregate in `IN (SELECT ...)` next to a window function: wrong "misuse" error, or a panic (still on Turso's newest code, 12 Nov) | [#11796](https://github.com/tursodatabase/turso/issues/11796) | [#11797](https://github.com/tursodatabase/turso/pull/11797) | **open** (filed 13 Nov) |

A fifth one, a DataFusion internal error with a scalar subquery inside `VALUES` (DF-02), was filed on
13 Nov with a fix (`docs/bughunt/datafusion/DF-02-*` on branch `generalized`).

## One-command reproduction

```sh
sudo bash scripts/reproduce.sh
```

On Ubuntu 22.04/24.04 this installs the build packages, builds PostgreSQL at `26bd08fb` with
assertions (about 10 minutes on 4 cores), installs the Python dependencies, starts one server as
the user `pg`, runs one 150-second fuzzing trial and prints the reported bugs the trial found.
Output of the run on 13 Nov 2026 (ids as in `src/known_bugs/known_bugs.yaml`):

```
== 6/6 result
Known bugs reproduced: 10 of 10
  - audit-f1          # NOT IN anti-join
  - audit-f2          # IGNORE NULLS hang
  - c-01              # duplicate statistics expression
  - esi-nonfinite     # non-finite MCV frequencies
  - pgbug-19768       # JSON_TABLE
  - pgbug-19771       # to_char
  - pgbug-19793       # range @> NULL
  - pgbug-19802       # MERGE
  - pgbug-19803       # parallel Append
  - pgbug-19826       # corr() under partial aggregation
```

The bugs found by the generalized fuzzer (DuckDB, Turso, DataFusion) have their own one-command
reproduction on branch `generalized`: `bash scripts/reproduce_generalized.sh` (5 of 5).

## Build and run

Exact dependencies (the versions of the tested run are pinned in
[`src/requirements-lock.txt`](src/requirements-lock.txt)):

| Dependency | Version tested |
|---|---|
| OS | Ubuntu 24.04.5 LTS (x86-64), 4 cores, 16 GB RAM |
| C toolchain for PostgreSQL | gcc 13.3.0, bison, flex, libreadline, zlib, libssl, libicu, libxml2 (`scripts/reproduce.sh` installs them) |
| PostgreSQL | master at `26bd08fb` (20devel, `--enable-cassert --enable-debug`); reference 18.6 (`REL_18_STABLE`) |
| Python | 3.13.16 (3.10 or newer works) |
| Python packages | PyYAML 6.0.1, psycopg 3.3.6 (binary), matplotlib 3.11.2, numpy 2.5.3, scipy 1.18.1, pytest 9.1.1 |

```sh
cd src && pip install -r requirements-lock.txt
python -m pytest -q                                   # 151 unit tests, no database needed
cd .. && bash scripts/setup_env.sh                    # build master (assertions) and the 18.6 reference
cd src
python -m pgfuzz -q sample configs/local.yaml -n 300 --execute --seed 1   # generate and run 300 test cases
python -m pgfuzz run configs/rq1.yaml                 # RQ1/RQ2 arms: 5 trials x 1 h each
python -m pgfuzz run configs/rq3.yaml                 # RQ3: re-injected bug benchmark
python -m pgfuzz report results/<experiment>          # tables, Mann-Whitney U, A12, plots
python -m pgfuzz precision ../triage/verdicts.yaml    # RQ2 precision per oracle
python3 ../paper/scripts/make_tables.py               # regenerate the paper's tables
cd ../paper && make && sh scripts/check.sh            # build and check the paper
```

Step-by-step instructions for every experiment with expected outputs:
[`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md).
Tool manual: [`src/README.md`](src/README.md). Never commit API keys.

## Results in one page (details: [`docs/RESULTS_ANALYSIS.md`](docs/RESULTS_ANALYSIS.md), paper section 4)

* Base: PostgreSQL master `26bd08fb`, assertions on; 5 trials x 1 h per arm.
* **RQ1** typed grammar 36.7% of backend lines vs 22.2% for random mutation; 99% vs 26% valid statements; oracles double the plan shapes.
* **RQ2** 93 triaged candidates: 8 real, 15 duplicates of real bugs, 42 false positives (from a few classes, all fixed), 28 flaky.
  Ten bugs reported upstream (table above).
* **RQ3** benchmark of 23 reverted fixes: the best arm found 2 of 20 observable bugs in 1 h; none of the 8 wrong-result bugs.
* **RQ4** LLM extension: +5 SQL features, no coverage gain, 4 of 10 commits accepted.
* **Deviation from the plan:** the LLM was Google Gemini Flash (free tier) through the tool's manual mode;
  fixes to the oracles after the campaigns were not re-measured.

## Layout

| Path | Content |
|---|---|
| `src/` | the tool (`src/pgfuzz`), 151 unit tests (`src/tests`), grammar, configs; see [`src/README.md`](src/README.md) |
| `harness/` | PostgreSQL server control used by the executor (local builds, Docker image, backtraces) |
| `paper/` | the final paper, [`paper/paper.pdf`](paper/paper.pdf) |
| `paper-source/` | its LaTeX source (ACM `sigconf`; `make`, `sh scripts/check.sh`); tables are generated by `paper-source/scripts/make_tables.py` |
| `runs/memberA-rq3/`, `runs/memberB-rq1-llm/` | raw data of the RQ3 and RQ1/RQ2/RQ4 campaigns, reports, LLM ledger and driver |
| `triage/verdicts.yaml` | verdict for every bug candidate (precision ledger; `pgfuzz precision`) |
| `docs/bughunt/` | bug reports, reproducers, patches, the differential scripts of the bug hunt; `docs/evidence/` smoke and tool evidence |
| `docs/presentation/` | final presentation and class talk (Beamer; `make` builds slides and speaker notes) |
| `docs/progress_meetings/` | progress meetings 1 and 2: reports, slides, study guide |
| `docs/complete_guide/` | the complete project document (LaTeX) |
| `docs/generalized/` | pointer to the generalized fuzzer (branch `generalized`) |
| `docs/EXECUTION_PLAN.md`, `docs/RESULTS_ANALYSIS.md` | commands for every campaign with expected outputs, analysis of the results |
| `scripts/` | `reproduce.sh`, server builds, campaign and benchmark scripts |
| `completion/` | the submission package |

## Team and contributions

Every member can explain every part. The paper's signed "Statement of Contributions" records who
did most of the work on each part, and the commit history shows the same split (GitHub users
`v28k` = Venu Kummari, `Blazing-bhuvi` = Bhuvan Chilukuti, `doma2542` = Gowtham Reddy).

## Dates

Paper and repository due 13 November 2026, 23:59 IST; final presentation in the end-semester week (14–21 November 2026).
