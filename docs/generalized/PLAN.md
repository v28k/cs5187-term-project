# Generalizing the fuzzer: plan (branch `generalized`, started 2 Nov 2026)

## Goal

Turn the PostgreSQL fuzzer into a **target-independent, grammar- and oracle-driven fuzzer for
SQL engines**, evaluate it on several engines, find and fix new bugs (GitHub issues and PRs
where the project accepts them), and write a paper for a top software-engineering / testing
venue with a deadline around January 2027 (check the CFPs; ISSTA usually has a late-January
deadline; ICSE and FSE have later cycles).

## The paper's claim (what must be true at the end)

1. **One tree, many engines.** Typed derivation trees plus a small per-engine *dialect overlay*
   give valid SQL on every target; the same tree-based oracles (TLP, NoREC, expression rewrites,
   plan variants, cross-version, hang, CERT) apply unchanged.
2. **Oracle precision is measured, not assumed,** on every target (verdict ledger per target).
3. **Knowledge transfer by LLM, gated by the engine:** an LLM turns an engine's own regression
   tests and recent commits into grammar fragments; a server-side gate (parse, use, validity,
   coverage) accepts them.
4. **Bugs:** new, confirmed and fixed bugs on several engines, with PRs where possible.

## Targets (in order)

| Target | Why | How we run it | Where bugs go |
|---|---|---|---|
| PostgreSQL | existing, 11 reports, 3 fixed | server (cassert build) | pgsql-bugs, patches |
| DuckDB | very active, fast fixes, nightlies on pip | in-process, in a worker subprocess (survives aborts) | GitHub issues and PRs |
| Apache DataFusion | Rust, very PR-friendly, many open SQL corners | build `datafusion-cli` from `main` (cargo) or python bindings | GitHub issues and PRs |
| SQLite | reference for a cross-engine oracle; hard target | stdlib `sqlite3` / CLI from trunk | forum (no PRs) |
| later, if time | MySQL/MariaDB, CockroachDB, TiDB | server | GitHub / JIRA |

## Tasks

| # | Task | Output |
|---|---|---|
| G1 | **Target abstraction**: a `Target` description = executor adapter + dialect overlay + schema + planner knobs (plan variants) + error taxonomy (which errors are bugs) + version for cross-version. Port PostgreSQL to it without behaviour change (all 151 tests pass). | `pgfuzz/targets/`, `targets/postgres/` |
| G2 | **Dialect layering of the grammar**: split `postgres.pgg` into a portable core (`core.pgg`) and overlays (`postgres.pgg`, `duckdb.pgg`, `datafusion.pgg`, `sqlite.pgg`); `include`/override support in the grammar DSL. | grammar files, DSL change, tests |
| G3 | **DuckDB target**: executor in a crash-isolating subprocess, error classification (`INTERNAL Error`, `FATAL`, aborts/signals), plan variants via DuckDB settings and optimizer switches, cross-version against the last release, schema + data. | first DuckDB campaign |
| G4 | **DataFusion target**: build `main`, executor via `datafusion-cli` or Python bindings, error classification (`Internal error`, panics), optimizer-rule toggles as plan variants. | first DataFusion campaign |
| G5 | **SQLite target** and **cross-engine differential oracle** on the portable subset, with normalisation of known semantic differences (gated by triage). | new oracle + precision |
| G6 | **LLM grammar extension from test suites**: mine each engine's regression tests (DuckDB `test/sql/*.test`, DataFusion `*.slt`, PostgreSQL `regress/sql`) and recent commits; LLM proposes fragments; the gate validates on the target. | ledger per target |
| G7 | **Harness hardening**: kill orphaned workers on stop, crash/hang isolation per target, signature de-duplication across targets, auto-triage + report drafts for GitHub. | robustness |
| G8 | **Evaluation design for the paper**: RQs across targets; baselines SQLancer (supports DuckDB, PostgreSQL, SQLite, DataFusion) and SQLsmith where possible; ≥10 trials × fixed budget; coverage where builds allow; re-injected bug benchmark for one more engine (DuckDB fixes). | configs, scripts |
| G9 | **Bug campaigns** on DuckDB nightly and DataFusion main; triage, issues, PRs with fixes. | issues / PRs |
| G10 | **Paper rewrite** for the venue (new title, framing, related work on SQLancer, SQLRight, Squirrel, Griffin, Sedar, THANOS-like and LLM fuzzers), artifact. | draft by mid January |

## Order of work

1. G1 + G3 first (DuckDB gives the fastest bug feedback), then G7, then G4, G2 in parallel as needed.
2. Bug campaigns (G9) start as soon as a target runs; findings go into `docs/bughunt/<target>/`.
3. G6, G5, G8 next; G10 continuously, final push in January.

## Rules

- Report a bug only after: reproduce ×3 on the newest nightly/main, minimal self-contained
  reproducer, duplicate search (issues + recent commits), root cause when possible.
- One target never breaks another: the PostgreSQL configs and results stay reproducible.
