# `src/`: pgfuzz, the evaluation and experiment harness

Project **A3: LLM-guided grammar-aware fuzzing of PostgreSQL**. The study
compares three fuzzer configurations under the same budget:

```
Random/Mutation  ->  Grammar-only  ->  Grammar + LLM
```

This folder holds the shared experiment infrastructure (Stage 1, Member C):
the plug-in interfaces, the failure oracle, the log format, the experiment
runner, statistics and the report generator. Member A's harness plugs in as an
`Executor`, and Member B's generators plug in as `Generator`s.

| Stage 1 part | Owner | Where it plugs in |
|---|---|---|
| Instrumented PostgreSQL + Docker harness, coverage | Member A | `Executor` (or use `pgfuzz.reference.pg_executor` directly) |
| Query representation, random/mutation baseline | Member B | `Generator` |
| Eval skeleton, logging format, experiment runner | Member C | everything in `pgfuzz/` |

## Requirements

Python 3.10 or newer. Versions tested: Python 3.12.7, PyYAML 6.0.1, psycopg 3.3.4,
matplotlib 3.8.2, pytest 7.4.3 (Windows 11). Install with:

```sh
cd src
pip install -r requirements.txt
```

## Quick start

All commands run from `src/`.

```sh
python -m pytest                                   # 84 tests after the random baseline was added
python -m pgfuzz run configs/smoke.yaml            # whole pipeline on a simulated server, ~40 s
python -m pgfuzz selftest configs/stage1.yaml      # acceptance checks against the real harness
python -m pgfuzz run configs/stage1.yaml -j 4      # the real Stage 1 experiment
```

`configs/smoke.yaml` uses `MockExecutor`, a simulated server with planted
"bugs". It tests the tooling only. **Never report its numbers.** The report
prints a warning when an experiment used it.

## Commands

| Command | What it does |
|---|---|
| `run CONFIG [-j N] [--only a,b] [--trials N] [--fresh] [--dry-run]` | Runs every (config, trial) pair. Re-running resumes: finished trials are skipped. A report is built at the end. |
| `report EXPERIMENT_DIR [--out DIR]` | Builds `report.md`, CSVs, LaTeX tables and plots from the run logs. |
| `validate PATH` | Checks run logs against the log format. |
| `selftest CONFIG` | Ten acceptance checks for the executor: SQLSTATE mapping, continuing after errors, timeouts, no state leaks, recovery after a lost connection. |
| `replay CONFIG FILE.sql... [--repeat N] [--expect-bug]` | Runs SQL files and prints the oracle's verdict and signature. Use it to validate failures on a fresh server and to check known-bug PoCs. |
| `features FILE.sql... [--missing] [--each]` | Shows which SQL catalog features a corpus covers. |

## Architecture

```
            config.yaml
                 |
          runner/experiment.py  -- trials x configs, paired seeds, resume, parallel workers
                 |
          runner/trial.py       -- one budgeted fuzzing loop
           |            |
   Generator.next_testcase()  -->  Executor.execute()  -->  ExecResult (raw facts)
           ^                                                   |
           |                                         eval/oracle.py    -> Outcome per statement
           |                                         eval/signature.py -> dedup signature
           |                                         eval/known_bugs.py-> known-bug match
           |                                         eval/metrics.py   -> coverage, validity, features
           +------------ Generator.feedback(Feedback) <--------+
                                                               |
                                                     runlog/ (events, timeline, failures, summary)
                                                               |
                                                     report/ (stats, tables, plots)
```

Package layout:

```
pgfuzz/core/       types.py (TestCase, ExecResult, Outcome, ...), interfaces.py, plugins.py, sqlsplit.py
pgfuzz/eval/       oracle.py, signature.py, features.py, metrics.py, known_bugs.py, stats.py
pgfuzz/runlog/     schema.py (format v1 + validator), writer.py, reader.py
pgfuzz/runner/     config.py, trial.py, experiment.py, selftest.py
pgfuzz/report/     report.py
pgfuzz/reference/  mock_executor.py, pg_executor.py, generators.py
pgfuzz/grammar/    typed .pgg engine and GrammarGenerator
generator/         Stage 1 random/mutation baseline (AST seeds, text mutation)
configs/           smoke.yaml (mock), stage1.yaml (random + grammar), local.yaml, hunt.yaml
corpus/            schema.sql (shared DB state), seeds/ (seed statements)
known_bugs/        known_bugs.yaml (catalog for the known-bug metric)
tests/             unit and end-to-end tests
```

## Plug-in contract

Plug-ins are named in configs as `"package.module:ClassName"`. The runner builds
them with the config's `params` as keyword arguments.

The random/mutation arm is ``generator.random_generator.generator:RandomGenerator``
(Member B, stage 1). Its seeds are built from ``corpus/schema.yaml``; mutations
are text-level and unguided. The grammar arm is
``pgfuzz.grammar.generator:GrammarGenerator``.

### Generators (Member B, later the LLM arm)

```python
from pgfuzz.core import Generator, GeneratorContext, TestCase, Feedback

class GrammarGenerator(Generator):
    name = "grammar"

    def __init__(self, grammar_file: str, max_depth: int = 8): ...

    def setup(self, ctx: GeneratorContext) -> None:
        self.rng = ctx.rng            # draw ALL randomness from ctx.rng (reproducible trials)

    def next_testcase(self) -> TestCase | None:
        return TestCase(["CREATE TABLE ...", "SELECT ..."], meta={"rules": [...]})

    def feedback(self, fb: Feedback) -> None:   # optional; unguided baselines ignore it
        ...  # fb.outcome, fb.statement_outcomes, fb.new_features, fb.new_signature, fb.coverage
```

A test case is an ordered list of statements, each without a trailing `;`.
`meta` is free-form provenance, such as grammar rules, the mutation operator or the
LLM prompt id. It is stored with every logged test case.

### Executors (Member A)

`pgfuzz.reference.pg_executor:PostgresExecutor` already implements the contract
for any reachable PostgreSQL. Point its `dsn` at the Docker container, mount the
server log and set `server_log`, and give it a `coverage_command` that prints
coverage as JSON. A custom executor must:

1. return one `StatementResult` per statement, in order;
2. keep going after a failing statement, and mark statements after a lost connection `SKIPPED`;
3. not leak database state between test cases (or declare it in `describe()`);
4. recover on its own after a crash (wait for crash recovery, reconnect);
5. report facts only (SQLSTATE, message, connection loss, server-log lines,
   backtrace if a core dump was captured) and never decide what counts as a bug.

`python -m pgfuzz selftest <config>` checks points 1 to 4.

## Failure oracle

`eval/oracle.py` classifies every statement, and the test case takes its worst outcome:

| Outcome | Rule | Bug candidate |
|---|---|---|
| `syntax_error` | SQLSTATE 42601 | no |
| `semantic_error` | other class 42, 0A, 25, 3D, 3F, ... | no |
| `runtime_error` | class 22, 23, 40, P0, other | no |
| `timeout` | 57014 (statement_timeout) | no |
| `resource_limit` | class 53, 54; XX000 `invalid memory alloc request size` | no |
| `connection_terminated` | 57P01 / 57P04 / 57P05 (orderly) | no |
| `internal_error` | XX000 (`elog(ERROR)` invariant violations) | **yes** |
| `data_corruption` | XX001, XX002 | **yes** |
| `panic` | `PANIC:` in the server log | **yes** |
| `crash` | lost connection, 57P02, `terminated by signal` in the log | **yes** |
| `assertion` | `TRAP: failed Assert(...)` (PG 16+) or `TRAP: FailedAssertion(...)` in the log | **yes** |

Assertion failures are only visible on a server built with `--enable-cassert`.
The executor records `debug_assertions` in the run manifest and adds a warning
when assertions are off.

**Deduplication** (`eval/signature.py`). Signatures are listed from strongest to weakest:
the top 5 non-generic stack frames, then the assertion file and expression, then the
SQLSTATE and the error message with literals, numbers and identifiers abstracted.
A crash without a backtrace falls back to a weak key: the signal plus the verb and SQL
features of the crashing statement. The client-side text "server closed the connection"
is identical for every crash, so it is never part of a key. Every signature records its
strength, so you can report counts that use only strong signatures.

## Metrics

Definitions, as implemented in `eval/metrics.py`:

- **Code coverage**: lines, branches or edges reported by the executor's `coverage_command`,
  sampled every `coverage_interval_s`.
- **Parse-valid rate**: the share of executed statements not rejected by the parser (not 42601).
- **Valid-query rate**: the share of executed statements that completed without error.
- **SQL feature coverage**: distinct features from a fixed catalog of 148 SQL constructs
  (`eval/features.py`), counted only in parse-valid statements.
- **Feature pairs**: distinct pairs of features that occur together in one statement.
  Optimizer bugs often need such combinations.
- **Query diversity**: distinct statement shapes, with literals and identifiers abstracted.
- **Unique bug candidates**: distinct signatures with a bug-candidate outcome, plus the time to the first one.
- **Execution efficiency**: statements and test cases per second, and mean execution time.
- **Known bugs reproduced**: signatures that match an entry in `known_bugs/known_bugs.yaml`.

## Evaluation protocol

These rules are built into the runner and the report:

- The same wall-clock budget for every arm. The budget starts after the executor has started.
- Several trials per arm. Trial *k* of every arm uses the same seed (a paired design).
  Use at least 10 trials for the final evaluation (Klees et al., CCS 2018).
- The report gives the median and IQR per arm, a two-sided Mann-Whitney U test, and the
  Vargha-Delaney A12 effect size. Comparisons cover consecutive arms (Random vs Grammar,
  Grammar vs Grammar+LLM) and each arm against the `baseline`.
- Every database statement runs against the same shared state (`corpus/schema.sql`).
- Every trial stores its full provenance in `manifest.json`: config, seed, plug-in
  parameters, server version, assertion setting, Python and platform versions, and git commit.

## Log format (v1)

```
results/<experiment>/
  experiment.json, experiment.yaml       resolved config copy
  <config>/trial-NN/
    manifest.json                        provenance
    events.jsonl                         one record per test case: outcome, culprit, SQLSTATE, signature, new features
    timeline.jsonl                       metric snapshots over time (for coverage-over-time plots)
    summary.json                         final metrics + every signature
    failures/<signature>/                failure.json, testcase.sql (replayable), repro-K.sql
  report/                                report.md, trials.csv, comparison.csv, bugs.csv, table_*.tex, timeline_*.png
```

The field-level schema is in `pgfuzz/runlog/schema.py`. `python -m pgfuzz validate`
enforces it. `results/` is git-ignored. Copy the final experiment directory used
for the paper into `paper/data/`, as `paper/data/README.md` requires.

## Workflow for a found failure

1. `python -m pgfuzz replay configs/stage1.yaml results/.../failures/<sig>/testcase.sql --repeat 3`
   checks that the failure reproduces on a fresh connection.
2. Re-run it on a fresh container to rule out leftover state.
3. Check the failure against the latest PostgreSQL release and `master` before you
   report it to pgsql-bugs. (Minimization comes in a later stage.)
