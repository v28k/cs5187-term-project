**Title:** Fix min/max over nested values computed by a subquery ("Cannot copy BoundSubqueryExpression")

**Base branch:** `main` (DuckDB has no PR template; the description below follows CONTRIBUTING.md:
problem, solution, issue number, tests)

**Body:**

Fixes #ISSUE

Since min/max apply collations to nested values (2ef9f76b2e), `BindMinMax` and `MinMaxNBind` copy the argument
for every STRUCT, LIST and ARRAY input before checking whether a collation applies to the nested type. Copying a
`BoundSubqueryExpression` throws, so these queries fail on 2.0.0 and `main` (they worked in 1.5.6):

```sql
CREATE TABLE a (x INTEGER);
INSERT INTO a VALUES (1), (2);
SELECT min((SELECT [1])) FROM a;      -- Serialization Error: Cannot copy BoundSubqueryExpression
SELECT max((SELECT [x]), 1) FROM a;   -- same
```

This PR checks the collation on a placeholder `BoundReferenceExpression` of the argument type first, and copies the
argument only when a collation applies. When it does, the same collation is pushed onto the copy as before, so
collated min/max is unchanged. Both the plain and the N variant use the new helper `GetCollatedMinMaxArgument`.

An argument that needs a collation and contains a subquery (for example `min((SELECT 'B'))` under
`SET default_collation = 'nocase'`) still fails as it already did in 1.5.6; that needs the value and the collated key
to share one projected expression, which I left out of this fix.

Tests: `test/sql/aggregate/aggregates/test_minmax_subquery_argument.test` covers LIST, STRUCT, LIST(VARCHAR) and ARRAY
arguments, a correlated subquery, `EXISTS` inside `CASE`, and `max(x, n)`. `test/sql/collate/*`,
`test/sql/subquery/*`, `test/sql/function/list/*` and `test/sql/aggregate/*` pass locally (except
`test_string_agg_overflow.test_slow`, which fails the same way on `main` without this change), and so does the
fast `unittest` suite.
