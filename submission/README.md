# CS-5187 term project A3: submission

**LLM-guided grammar-aware fuzzing of PostgreSQL** (tool `pgfuzz`, called **Arbor** in the paper).
Team: Venu Kummari, Bhuvan, Gowtham. Repository: <https://github.com/v28k/cs5187-term-project>
(branch `main` = course project; branch `generalized` = the extension to other SQL engines).

## Files in this folder

| File | What it is |
|---|---|
| [`paper.pdf`](paper.pdf) | final report, ACM/FSE format (anonymous review format; 12 pages + references). Source: `paper/` (`make`, `sh scripts/check.sh`) |
| [`slides/final_presentation.pdf`](slides/final_presentation.pdf), [`.pptx`](slides/final_presentation.pptx) | final presentation (18 slides) and its [speaker notes](slides/final_presentation_speaker_notes.md) |
| [`slides/class_talk.pdf`](slides/class_talk.pdf), [`.pptx`](slides/class_talk.pptx) | short class talk (7 minutes) and its [speaker notes](slides/class_talk_speaker_notes.pdf) |
| [`progress/`](progress/) | progress-meeting material as presented: meeting 1 report and slides, meeting 2 report and slides (numbers in these are the state on their dates) |

## What we built

A fuzzer that generates SQL as typed derivation trees from a 78-rule grammar, turns the trees
into checks that know the right answer (TLP, NoREC, typed expression rewrites, plan-variant,
cross-version, row-level-security and cardinality-estimate oracles, plus crash, assertion,
internal-error and hang detection), reduces every finding on its tree and its tokens, and
extends the grammar from recent PostgreSQL commits with an LLM behind a server-side validation
gate. Evaluation: RQ1 coverage and validity, RQ2 bugs and oracle precision, RQ3 a benchmark of 23
re-injected real bugs, RQ4 the LLM extension (details and numbers: `paper.pdf`, section 5).

## Bugs found (state on 8 Nov 2026, as in the paper's bug table)

Nine PostgreSQL bugs reported; **six fixed upstream, five of them with our patches**; one more
confirmed with our patch posted.

| Bug | Report | Found by | State |
|---|---|---|---|
| parallel `Append` assertion | BUG #19803 | TLP (LLM-fragment arm) | fixed |
| `to_char(NaN)` breaks `NORMALIZE` | BUG #19771 | assertion | fixed (our patch) |
| `JSON_TABLE` assigns no collations | [BUG #19768](https://www.postgresql.org/message-id/flat/19768-3633daa830be95db@postgresql.org) | assertion | fixed (our patch) |
| `NOT IN` anti-join ignores a cast | pgsql-bugs | TLP | fixed (our patch) |
| `IGNORE NULLS` frame never returns | pgsql-bugs | hang | fixed (our patch) |
| duplicate statistics expression | pgsql-bugs | assertion | fixed (our patch) |
| `MERGE`: SubPlan with no parent | BUG #19802 | internal error | confirmed, patch |
| `range @> NULL` folded to a constant | [BUG #19793](https://www.postgresql.org/message-id/19793-16d3a1bf33dff0fb@postgresql.org) | `(SELECT e)` rewrite | reported, patch |
| non-finite imported MCV frequencies | pgsql-hackers | CERT estimate | patch |

Reproducers, reports and patches: `docs/bughunt/` (and `docs/bughunt/new/`). The fuzzer
rediscovers all nine in one 150-second run (`src/configs/rediscover.yaml`, evidence in
`docs/evidence/rediscovery/`). Earlier documents (`docs/RESULTS_ANALYSIS.md`,
`docs/generalized/HANDOFF.md`) record earlier states of these bugs; the table above is current.

Extension (branch `generalized`, beyond the course scope): the same core now also tests DuckDB,
SQLite, Turso and Apache DataFusion. It produced bug reports with fixes filed to Turso
([#11594](https://github.com/tursodatabase/turso/issues/11594) /
[PR #11595](https://github.com/tursodatabase/turso/pull/11595)), DuckDB
([#28551](https://github.com/duckdb/duckdb/issues/28551) /
[PR #28552](https://github.com/duckdb/duckdb/pull/28552)) and DataFusion
([#27235](https://github.com/apache/datafusion/issues/27235) /
[PR #27236](https://github.com/apache/datafusion/pull/27236)).

## Artifact: how to run

Requirements: Linux, Python 3.10+, a C toolchain for building PostgreSQL. All commands from the
repository root.

```sh
cd src && pip install -r requirements.txt
python -m pytest -q                                   # 151 unit tests, no database needed
cd .. && bash scripts/setup_env.sh                    # builds PostgreSQL master (assertions, gcov),
                                                      # the 18.6 reference and the benchmark servers
cd src
python -m pgfuzz -q sample configs/local.yaml -n 300 --execute --seed 1   # generate + run 300 test cases
python -m pgfuzz run configs/rediscover.yaml          # rediscovers all 9 reported bugs (within 150 s)
python -m pgfuzz run configs/rq1.yaml                 # RQ1/RQ2 arms (5 trials x 1 h each)
python -m pgfuzz run configs/rq3.yaml                 # RQ3 re-injected bug benchmark
python -m pgfuzz report ../results/<experiment>       # tables, Mann-Whitney U, A12, plots
python -m pgfuzz precision ../triage/verdicts.yaml    # RQ2 precision ledger
python3 ../paper/scripts/make_tables.py               # regenerate the paper's tables
```

Step-by-step instructions for every experiment, expected outputs and timings:
`docs/TEAM_RUNBOOK.md`. Tool documentation: `src/README.md`.

## Evidence

| Claim | Evidence |
|---|---|
| campaign data behind RQ1-RQ4 | `runs/memberA-rq3/`, `runs/memberB-rq1-llm/` (raw logs, reports, LLM ledger) |
| triage verdict of every candidate (RQ2 precision) | `triage/verdicts.yaml` |
| bug reproducers, upstream reports, patches | `docs/bughunt/` |
| all nine bugs rediscovered by the tool | `docs/evidence/rediscovery/` |
| benchmark smoke test, tree reduction | `docs/evidence/rq3_smoke2/`, `docs/evidence/tree_reduction/` |
| analysis of all results | `docs/RESULTS_ANALYSIS.md` |
| tests pass | `cd src && python -m pytest -q` (151 passed on 8 Nov 2026) |
