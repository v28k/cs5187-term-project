# DF-02: scalar subquery inside VALUES: "Internal error: ScalarSubqueryExpr evaluated before the subquery was executed"

| | |
|---|---|
| Status | **ready to file: issue + fix PR** (not filed) |
| Target | Apache DataFusion (https://github.com/apache/datafusion) |
| Kind | INTERNAL error on a valid query (DataFusion itself says "likely caused by a bug in DataFusion's code") |
| Affected | **`main` bc86321 (8 Nov 2026, 57.0.0-dev), `datafusion-cli` built from source**; datafusion-python 55.0.0 (DataFusion 55, where physical scalar-subquery evaluation is new) |
| Fix | `fix.patch` (written and tested here) |
| Found by | grammar fuzzer, DataFusion target, internal-error oracle (8 Nov 2026) |

## Reproducer

```sql
VALUES ((SELECT 1), 5);
```

Actual: `Internal error: ScalarSubqueryExpr evaluated before the subquery was executed.` Expected: `(1, 5)`.
Also fails: `SELECT * FROM (VALUES ((SELECT min(x) FROM (VALUES (1), (2)) AS v(x)), 5)) AS t(a, b)`,
`INSERT INTO v VALUES ((SELECT 1), 5)`, `INSERT INTO v SELECT * FROM (VALUES ((SELECT max(a) FROM v), 6)) AS s(a, b)`.

## Root cause

`datafusion/core/src/physical_planner.rs`: `LogicalPlan::Values` is planned with
`MemorySourceConfig::try_new_as_values` (`datafusion/datasource/src/memory.rs`), which evaluates every row expression
against a one-row placeholder batch **while the physical plan is built**. With
`enable_physical_uncorrelated_scalar_subquery` (default on), an uncorrelated scalar subquery becomes a
`ScalarSubqueryExpr` that reads its value from a results container filled by the `ScalarSubqueryExec` wrapping the
plan, at execution time. At planning time the container is empty, so `ScalarSubqueryExpr::evaluate` returns the
internal error (`datafusion/physical-expr/src/scalar_subquery.rs`).

## Fix (`fix.patch`)

A new match arm for `LogicalPlan::Values` whose rows contain an `Expr::ScalarSubquery`: each row becomes a
`ProjectionExec` (aliases = the VALUES schema's field names) over a `PlaceholderRowExec`, and the rows are combined
with `UnionExec::try_new` (one row: the projection itself). These are evaluated at execution time inside
`ScalarSubqueryExec`. VALUES lists without scalar subqueries keep the existing path. `EXPLAIN VALUES ((SELECT 1), 5),
(2, 3)` shows `ScalarSubqueryExec → UnionExec → ProjectionExec → PlaceholderRowExec`.

## Tests run (8 Nov 2026, `--profile ci`, `main` bc86321 + patch)

- new cases in `subquery.slt` (one-row and two-row VALUES with scalar subqueries in different columns): fail on `main`
  (internal error) and pass with the patch.
- `cargo test --profile ci -p datafusion-sqllogictest --test sqllogictests` (**all 546 test files**, run with both
  DataFusion fixes applied): pass. On the DF-02 branch alone: the 9 files matching `subquery`, `values`, `insert`,
  `explain` pass.
- `cargo clippy --profile ci -p datafusion --all-targets -- -D warnings`: clean; `cargo fmt --all`: clean.
- Not run here: the extended `cargo test --workspace` command from AGENTS.md (disk); CI runs it.

## Duplicate search (8 Nov 2026)

GitHub search API, apache/datafusion: `"ScalarSubqueryExpr evaluated before" is:issue|is:pull-request` → nothing;
`VALUES scalar subquery created:>2026-06-01` → only correlated-subquery issues (#26508, #26505, #26704, #26710, …),
none about VALUES. Web search → only the source file and PR #21240's review (design of `ScalarSubqueryExec`).
`main` to bc86321: related fixes #26836, #26723, #26544, none about VALUES.

## Files

`issue.md`, `pr.md`, `fix.patch`, `tests.slt.diff`, `repro.sql`, `steps.md`.
