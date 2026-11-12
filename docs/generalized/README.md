# Generalized fuzzer

The extension of the fuzzer to DuckDB, SQLite, Turso and Apache DataFusion lives on branch
[`generalized`](https://github.com/v28k/cs5187-term-project/tree/generalized). Its code, configurations,
plan, evaluation results and bug packages are only there.

What it adds to the PostgreSQL fuzzer on this branch:

* one driver per engine in a crash-isolated worker process, and a dialect overlay per engine on the
  same typed grammar (with an overlay miner that drafts the overlay from measured failure rates);
* optimizer-rule firing (a rule fires if switching it off changes the plan) as feedback, coverage and
  localization signal on release builds;
* Z3 data synthesis for non-vacuous metamorphic checks, learned value normalizers for cross-engine
  comparison, engine test suites as seeds;
* rule kernels (minimal queries that trigger one optimizer rule), a composition oracle over pairs of
  kernels, identity grafts, a state-restoration oracle and cross-engine kernel transfer;
* a pipeline from campaign to a filing package with a regression test in the engine's own format.

Bugs filed upstream with a fix and a regression test: Turso #11594 / PR #11595 and #11796 / PR #11797,
DuckDB #28551 / PR #28552 (approved by a maintainer), DataFusion #27235 / PR #27236, and DataFusion
DF-02 (13 Nov 2026). States: [`../../README.md`](../../README.md).
