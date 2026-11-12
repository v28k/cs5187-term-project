# T-08: issue and pull request as filed

**Status:** filed on 13 Nov 2026: issue [#11796](https://github.com/tursodatabase/turso/issues/11796), PR [#11797](https://github.com/tursodatabase/turso/pull/11797). Validated on Turso `main` 38b7d9de1 (12 Nov 2026). Before filing we searched the Turso issues on 12 Nov 2026 for "misuse of aggregate" and
"aggregate called in scalar context": no report of this case.

**Related, but not the same:** open PR tursodatabase/turso#11597 ("reject extension aggregates
where no aggregate is computed"). It would turn the `median()` panic into the same wrong
"misuse of aggregate" error that `max()` gives. Our query does compute an aggregate, so it
must not be rejected at all.

**Found by:** the crash oracle (the worker process died with a Rust panic) in the 11 Nov hunt
against pyturso 0.8.3. Failure `3308362ffef6`: a 1.7 kB generated query using
`PERCENTILE_DISC(...) IN (SELECT ...)` next to `FIRST_VALUE(0) OVER (...)`. Reduced by hand to
the four statements in `repro.sql`, then compared with SQLite.

## Issue title

```
Aggregate in IN (SELECT ...) is rejected as misuse when the query has a window function (panics for median())
```

## Issue body

````
An aggregate inside an `IN (SELECT ...)` expression in the select list fails when the same query
also has a window function. Built-in aggregates are rejected with "misuse of aggregate function",
and an extension aggregate such as `median()` or `percentile_disc()` panics. SQLite returns the
result, and Turso does too without the window function.

```sql
CREATE TABLE t(x INTEGER);
INSERT INTO t VALUES (1), (3);

SELECT max(x) IN (SELECT 1), count(*) OVER () FROM t;
-- SQLite: 0|1
-- Turso:  Parse error: misuse of aggregate function max()

SELECT sum(x) NOT IN (SELECT 4), row_number() OVER () FROM t;
-- SQLite: 0|1
-- Turso:  Parse error: misuse of aggregate function sum()

SELECT max(x) IN (SELECT 3) FROM t ORDER BY sum(x) OVER ();
-- SQLite: 1
-- Turso:  Parse error: misuse of aggregate function max()

SELECT median(x) IN (SELECT 2), count(*) OVER () FROM t;
-- expected: 1|1
-- Turso: panicked at core/ext/function.rs:91:18:
--        internal error: entered unreachable code: aggregate called in scalar context
```

Without the window function (`SELECT max(x) IN (SELECT 3) FROM t` returns 1) or with a
GROUP BY, the same expression works.

Cause: `rewrite_terminal_expr` in `core/translate/window.rs` moves a result expression that
contains a subquery (`InSelect`, `Exists`, `Subquery`, `SubqueryResult`) into the window's
source subquery as a whole, and always passes `contains_aggregates = false` for the new column.
The aggregate in the left operand of `IN` is then translated as a scalar function call.

#11597 would turn the panic into the same "misuse of aggregate" error, but these queries do
compute an aggregate, so they should not fail.

Checked on main 38b7d9de1 (12 Nov 2026) and pyturso 0.8.3. Found with a grammar-based SQL fuzzer.
I have a fix with a regression test and will open a PR.
````

## Pull request title

```
core/translate: compute aggregates in subquery expressions of window queries
```

## Pull request body

````
A query with a window function moves each result expression that holds a subquery (IN, EXISTS,
a scalar subquery) into the window's source subquery, but always marked the new column as
containing no aggregates. An aggregate in such an expression, e.g. the left operand of
`max(x) IN (SELECT ...)`, was then translated as a scalar call: a built-in aggregate failed with
"misuse of aggregate function max()", and an extension aggregate (median, percentile_disc, ...)
panicked with "aggregate called in scalar context".

The column is now marked as containing aggregates when the expression contains one of the
query's aggregates, so it is evaluated after aggregation, as it is without a window function.

Test: `sqlite/conformance/sqlite-sqltests/window/aggregate-in-subquery-operand.sqltest`
(IN, NOT IN, count(*), the window function in ORDER BY, with GROUP BY, and extension aggregates;
the extension test is skipped on SQLite, which has no median()).

Ran with the cli backend: the window, agg-functions and subquery corpora (1399 passed), all of
sqlite-sqltests (12726 passed; only big-db and big-db-mvcc failed, because the machine had less
free disk than the 2.2 GB database they write) and turso-sqltests + testing/shared-sqltests
(3661 passed).
````
