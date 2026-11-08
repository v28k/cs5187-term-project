**Title:** fix: evaluate scalar subqueries in VALUES rows at execution time

**Body** (sections of `.github/pull_request_template.md`):

## Which issue does this PR close?

- Closes #ISSUE.

## Rationale for this change

`VALUES ((SELECT 1), 5)` and `INSERT INTO t VALUES ((SELECT 1), 5)` fail with
`Internal error: ScalarSubqueryExpr evaluated before the subquery was executed`. The VALUES exec evaluates its rows
when the plan is built, but the value of an uncorrelated scalar subquery only exists once `ScalarSubqueryExec` has run.

## What changes are included in this PR?

When a row of a `LogicalPlan::Values` contains a scalar subquery, the physical planner plans each row as a
`ProjectionExec` over a `PlaceholderRowExec` and unions the rows (`UnionExec::try_new`, which returns the single
input for one row), so the row expressions are evaluated at execution time, inside `ScalarSubqueryExec`. VALUES lists
without scalar subqueries are planned as before (`MemorySourceConfig::try_new_as_values`).

## What is the testing strategy for this PR?

New cases in `subquery.slt` (section "Uncorrelated scalar subqueries in various expression contexts"): a one-row and
a two-row VALUES list with scalar subqueries in different columns. They fail on `main` with the internal error and
pass with this change. The whole sqllogictest suite passes locally
(`cargo test --profile ci -p datafusion-sqllogictest --test sqllogictests`).

## Are there any user-facing changes?

No API changes; these queries now run. `EXPLAIN` of such a VALUES list shows projections over placeholder rows
instead of a values data source.
