# Arbor: LLM-guided grammar-aware fuzzing of PostgreSQL

CS-5187 term project A3 (IIT Guwahati, 2026). Team: **Venu Kummari, Bhuvan Chilukuti, Gowtham Reddy**.
The tool is called `pgfuzz` in the code and **Arbor** in the paper. License: [MIT](LICENSE).
Course repository: <https://github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi>; working
repository with the `generalized` branch: <https://github.com/v28k/cs5187-term-project>.

Arbor generates SQL as typed derivation trees from a grammar of 78 rules, rewrites the trees into
metamorphic checks (TLP, NoREC, typed expression rewrites, a row-level-security check, a
cardinality-estimate check, plan-variant and cross-version oracles), detects crashes, assertion
failures, internal errors and hangs, reduces every finding on its tree and tokens, and extends the
grammar from recent PostgreSQL commits with an LLM behind a server-side validation gate.

* **Deliverables for submission:** [`completion/`](completion/README.md) (paper PDF and Overleaf
  source, slides, complete project guide, progress material, contributions, bug list).
* **Generalized fuzzer** (DuckDB, SQLite, Turso, DataFusion): branch
  [`generalized`](https://github.com/v28k/cs5187-term-project/tree/generalized), summary in
  [`docs/generalized/README.md`](docs/generalized/README.md).
* **Further techniques after the course paper** (branch
  [`generalised-improved`](https://github.com/v28k/cs5187-term-project/tree/generalised-improved)):
  optimizer-rule *kernels* (minimal queries that trigger one rule, learned by reduction, also from
  the engines' own test suites), a composition oracle over pairs of kernels, identity grafts, a
  state-restoration oracle for rolled-back test cases, and cross-engine kernel transfer. In 15-minute
  campaigns, kernel seeds raised the optimizer-rule pairs reached on DuckDB from 307 to 386 (also per
  test case) and on SQLite from 86 to 182 (there mostly because kernels run faster);
  `docs/generalized/results/` on that branch.

## Headline result

Arbor found **nine PostgreSQL bugs** that we reported upstream: **seven are fixed upstream, five of
them with our patches**, and the other two are under review with our patches. One command reproduces the fuzzer finding all
nine in a 150-second run (section "One-command reproduction").

## Upstream bug reports and their state (12 Nov 2026)

| # | Bug | Upstream report | State |
|---|---|---|---|
| 1 | parallel `Append` assertion in `create_append_path` | [BUG #19803](https://postgr.es/m/19803-1fcc1df108c54ab6@postgresql.org) | **merged**: fixed in `abda2a2c` (David Rowley), back-patched to 14 |
| 2 | `to_char()` NUL byte with a trailing decimal point (breaks `NORMALIZE`) | [BUG #19771](https://www.postgresql.org/message-id/19771-4f173b891525020c@postgresql.org) | **merged**: our patch, `776df8a6`, committed by Tom Lane |
| 3 | duplicate statistics expression: assertion in `dependencies_clauselist_selectivity` | [pgsql-bugs thread](https://www.postgresql.org/message-id/PN0P287MB0903563C70D8E5B81912E855A7602@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, `b0392c26`, committed by David Rowley, back-patched to 14 |
| 4 | `JSON_TABLE` assigns no collations (wrong result in 17/18, assertion on master) | [BUG #19768](https://www.postgresql.org/message-id/19768-3633daa830be95db@postgresql.org) | **merged**: our patch, committed by Amit Langote, back-patched to 17 |
| 5 | `NOT IN` anti-join ignores an implicit cast (wrong result on master) | [pgsql-bugs thread](https://www.postgresql.org/message-id/PN0P287MB090375874C6D5433282EC9DFA7642@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, committed by Richard Guo |
| 6 | `first_value`/`nth_value` with `IGNORE NULLS` never returns (ignores cancel) | [pgsql-bugs thread](https://www.postgresql.org/message-id/PN0P287MB09038F3BD9921EBACF5646F6A7632@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, committed by Tatsuo Ishii |
| 7 | `MERGE` into a partitioned table: "SubPlan found with no parent plan" | [BUG #19802](https://www.postgresql.org/message-id/19802-ef50a8f1a4b5deee@postgresql.org) | **merged**: fixed in `7a5559a6` (Tender Wang, committed by Dean Rasheed), back-patched to 15 |
| 8 | `range @> NULL` folded to a constant (wrong result in 17, 18, master) | [BUG #19793](https://www.postgresql.org/message-id/19793-16d3a1bf33dff0fb@postgresql.org) | **open**: reported with a patch |
| 9 | `pg_restore_extended_stats` accepts non-finite MCV frequencies | pgsql-hackers ([our patch](docs/bughunt/bhuvan/patches/0001-Reject-non-finite-MCV-frequencies-in-pg_restore_exte.patch)) | **open**: patch submitted |

Further reports: BUG #19826 (`corr()` and the `regr_*()` functions under partial aggregation; our
patch was reviewed and revised by Tom Lane, v3, and our v4 with the tests he asked for was sent on
12 Nov; all versions in `docs/bughunt/new/`), a Memoize/sublink error (`docs/bughunt/new/E-02-*`), and an independent
reproducer for BUG #19766. Reproducers and patches: [`docs/bughunt/`](docs/bughunt/).

Generalized fuzzer (branch `generalized`; new techniques on `generalised-improved`), each filed on
8 Nov 2026 with a fix and a regression test:

| Engine | Bug | Issue | Pull request | State |
|---|---|---|---|---|
| Turso | `percentile_disc`/`percentile_cont` with an expression argument | [#11594](https://github.com/tursodatabase/turso/issues/11594) | [#11595](https://github.com/tursodatabase/turso/pull/11595) | **open** (in review; test for a case found by a reviewer added 12 Nov) |
| DuckDB | `min`/`max` over a nested value computed by a subquery (2.0.0 regression) | [#28551](https://github.com/duckdb/duckdb/issues/28551) | [#28552](https://github.com/duckdb/duckdb/pull/28552) | **approved**: auto-merge enabled by a DuckDB maintainer, marked for the 2.0 backport |
| DataFusion | `UPDATE`/`DELETE` that repeat an expression fail on `__common_expr_1` | [#27235](https://github.com/apache/datafusion/issues/27235) | [#27236](https://github.com/apache/datafusion/pull/27236) | **open** (validated by a contributor, awaiting a committer) |

A fourth one, a Turso bug that still occurs on Turso's newest code (an aggregate in `IN (SELECT ...)`
next to a window function), has a fix and a test ready to file: `latestbugs/T-08-*` on branch
`generalised-improved`.

## One-command reproduction

```sh
sudo bash scripts/reproduce.sh
```

On Ubuntu 22.04/24.04 this installs the build packages, builds PostgreSQL at `26bd08fb` with
assertions (about 10 minutes on 4 cores), installs the Python dependencies, starts one server as
the user `pg`, runs one 150-second fuzzing trial and prints the reported bugs the trial found.
Output of the run on 9 Nov 2026 (ids as in `src/known_bugs/known_bugs.yaml`):

```
== 6/6 result
Known bugs reproduced: 9 of 9
  - audit-f1          # NOT IN anti-join
  - audit-f2          # IGNORE NULLS hang
  - c-01              # duplicate statistics expression
  - esi-nonfinite     # non-finite MCV frequencies
  - pgbug-19768       # JSON_TABLE
  - pgbug-19771       # to_char
  - pgbug-19793       # range @> NULL
  - pgbug-19802       # MERGE
  - pgbug-19803       # parallel Append
```

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
[`docs/TEAM_RUNBOOK.md`](docs/TEAM_RUNBOOK.md) and [`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md).
Tool manual: [`src/README.md`](src/README.md). Never commit API keys.

## Results in one page (details: [`docs/RESULTS_ANALYSIS.md`](docs/RESULTS_ANALYSIS.md), paper section 4)

* Base: PostgreSQL master `26bd08fb`, assertions on; 5 trials x 1 h per arm.
* **RQ1** typed grammar 36.7% of backend lines vs 22.2% for random mutation; 99% vs 26% valid statements; oracles double the plan shapes.
* **RQ2** 93 triaged candidates: 8 real, 15 duplicates of real bugs, 42 false positives (from a few classes, all fixed), 28 flaky.
  Nine bugs reported upstream (table above).
* **RQ3** benchmark of 23 reverted fixes: the best arm found 2 of 20 observable bugs in 1 h; none of the 8 wrong-result bugs.
* **RQ4** LLM extension: +5 SQL features, no coverage gain, 4 of 10 commits accepted.
* **Deviation from the plan:** the LLM was Google Gemini Flash (free tier) through the tool's manual mode;
  fixes to the oracles after the campaigns were not re-measured.

## Layout

| Path | Content |
|---|---|
| `src/` | the tool (`src/pgfuzz`), 151 unit tests (`src/tests`), grammar, configs; see [`src/README.md`](src/README.md) |
| `paper/` | the paper (ACM `sigconf`; `make`, `sh scripts/check.sh`); tables are generated by `paper/scripts/make_tables.py` |
| `runs/memberA-rq3/`, `runs/memberB-rq1-llm/` | raw data of the RQ3 and RQ1/RQ2/RQ4 campaigns, reports, LLM ledger and driver |
| `triage/verdicts.yaml` | verdict for every bug candidate (precision ledger; `pgfuzz precision`) |
| `docs/bughunt/` | bug reports, reproducers, patches; `docs/evidence/` smoke and tool evidence |
| `docs/beamer/` | final presentation and class talk (Beamer; `make` builds slides and speaker notes) |
| `docs/complete_guide/` | the complete project document (LaTeX) |
| `docs/final/`, `docs/class_talk/`, `docs/meeting/`, `docs/meeting2/` | earlier slide versions and progress meetings 1 and 2 |
| `scripts/` | `reproduce.sh`, server builds, campaign and benchmark scripts |
| `completion/` | the submission package |

## Team and contributions

Every member can explain every part. The paper's signed "Statement of Contributions" records who
did most of the work on each part, and the commit history shows the same split (GitHub users
`v28k` = Venu Kummari, `Blazing-bhuvi` = Bhuvan Chilukuti, `doma2542` = Gowtham Reddy).

## Dates

Paper and repository due 13 November 2026, 23:59 IST; final presentation in the end-semester week (14–21 November 2026).
