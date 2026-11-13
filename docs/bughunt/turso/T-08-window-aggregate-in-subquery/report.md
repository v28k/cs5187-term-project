# T-08: aggregate in `IN (SELECT ...)` in a query with a window function: misuse error, or a panic

| Field | Value |
|---|---|
| Status | **filed** 13 Nov 2026: issue [#11796](https://github.com/tursodatabase/turso/issues/11796), PR [#11797](https://github.com/tursodatabase/turso/pull/11797) |
| Found by | crash oracle (worker panic) in the 11 Nov campaign on pyturso 0.8.3; reduced by hand |
| Checked on | Turso `main` 38b7d9de1 (12 Nov 2026) and 0c9fe0dd9; pyturso 0.8.3 |
| Kind | wrong error on a valid query (built-in aggregates); process panic (extension aggregates) |

Reproducer: [`repro.sql`](repro.sql); expected and actual output: [`output.txt`](output.txt).

Cause: `rewrite_terminal_expr` in `core/translate/window.rs` moves a result expression that holds a
subquery (`IN`, `EXISTS`, scalar subquery) into the window's source subquery as a whole and marks the new
column as containing no aggregates, so an aggregate in it (the left operand of `max(x) IN (SELECT ...)`) is
translated as a scalar call.

Fix: [`0001-core-translate-compute-aggregates-in-subquery-expres.patch`](0001-core-translate-compute-aggregates-in-subquery-expres.patch):
mark the column as containing aggregates when the expression contains one of the query's aggregates.
Regression test: [`aggregate-in-subquery-operand.sqltest`](aggregate-in-subquery-operand.sqltest).
Issue and PR text: [`issue.md`](issue.md). The fuzzer's original finding: [`fuzzer-finding/`](fuzzer-finding/).
