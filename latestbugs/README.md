# Latest bugs (branch `generalised-improved`)

One folder per bug that is **validated on the engine's newest development code and ready to
file**. Each folder has `issue.md` (the exact title and text to paste), `repro.sql`, the expected
and actual output, and the versions it was checked on. You file; nothing here was filed by the tool.

## Ready to file

| Id | Engine | Bug | Checked on | Folder |
|---|---|---|---|---|
| T-08 | Turso | An aggregate in `IN (SELECT ...)` (e.g. `max(x) IN (SELECT 1)`) in a query that also has a window function is rejected with "misuse of aggregate function max()"; with `median()` or `percentile_disc()` the process panics. SQLite returns the result. Fix and regression test included. | `main` 38b7d9de1 (12 Nov 2026) | [`T-08-turso-window-aggregate-in-subquery/`](T-08-turso-window-aggregate-in-subquery/issue.md) |

## Found, but already fixed upstream (do not file)

Real bugs in the released package, checked against Turso `main` 0c9fe0dd9 (11 Nov 2026), where
they no longer reproduce. They count as findings of the fuzzer, not as reports.

| Id | Engine and version | Bug | Found by | Reproducer |
|---|---|---|---|---|
| T-06 | pyturso 0.8.3 | After a runtime error in a statement inside `BEGIN` (for example integer overflow in a `SELECT`), the transaction is silently ended: the next `INSERT` is committed on its own and `ROLLBACK` fails with "no transaction is active". SQLite keeps the transaction. | state-restoration oracle (new on this branch) | `already-fixed-upstream/turso-T06-transaction-lost-after-runtime-error.sql` (final count: 2 on 0.8.3, 1 on SQLite and on `main`) |
| T-07 | pyturso 0.8.3 | A correlated subquery in `HAVING` that reads a grouping column which is not in the select list sees NULL: `SELECT count(*) FROM t GROUP BY b HAVING (SELECT b) = 1` returns no row (SQLite and `main`: 2). | expression-rewrite oracle (`e` vs `(SELECT e)`) | `already-fixed-upstream/turso-T07-having-correlated-subquery.sql` |

## Checked and rejected (not bugs)

| Candidate | Why it is not a bug |
|---|---|
| ~890 Turso-vs-SQLite result differences in one campaign | follow-on noise: T-06 left rows behind in Turso, so later comparisons differed; plus the already-filed percentile bug (T-05). The state-restoration oracle now reports the first leak and resets the engine. |
| DuckDB: 4 rows by default, 5 rows with `projection_pullup` or `join_order` disabled | flaky (0 of 3 reproductions): the query groups by a `VARIANCE` result, a floating-point value that depends on parallel execution order |
| Turso: `SELECT max(c0), c0 FROM t` returns `c0` of another row than the max row (SQLite: the max row) | known upstream: issue #5545, PRs #10530 and #10544 (open) |
| Turso: `SELECT (SELECT max(t.c0)), count(*) OVER () FROM t` returns one row per input row; SQLite raises "misuse of aggregate" | same family as open issues #11480 and #9089 (aggregate of an outer column computed in the wrong query) |
| DuckDB nightly 2.1.0.dev (31 Oct): "BoundReferenceExpression should not be used here yet!" for an aggregate or window function whose argument holds a lambda, inside another lambda | already reported: duckdb#27720 (open) |
| DuckDB nightly: "Unrecognized expression type in logical operator visitor" for a window function that reads a lambda parameter, e.g. `list_transform([3], lambda x: sum(x) OVER ())` | already reported: duckdb#27983 (open) |
| DataFusion 55.0.0: `WHERE round(x, 2) = 10` on `DECIMAL(38,10)` fails with "Invalid comparison operation: Decimal128(38, 2) == Decimal128(38, 10)" (also an internal error in the CASE lookup table) | fixed on `main` by PR #23232 (24 Aug, after the 55.0.0 release): literal arguments are now passed at their coerced type, so `round` reports the same scale at planning and at run time |
| DataFusion 55.0.0: `SELECT TRUE UNION SELECT (c1 = 'a') IS NOT TRUE FROM tp` (nullable `c1`): "Physical input schema should be the same ..." (nullability) | fixed on `main` by PR #24244 (issue #24096, 24 Aug) |
| DataFusion 55.0.0: window `ORDER BY` an interval constant: "Cannot run range queries on datatype: Interval(MonthDayNano)" | already reported: datafusion#24915 (open) |
| DataFusion 55.0.0: `substr(s, cardinality(...))` rejected because the length is `UInt64` | the signature accepts only signed integers by design; the misleading "Internal error" wording is tracked in #20501 / #19004 |
| DataFusion: `UPDATE`/`DELETE` with `__common_expr_N`, and a scalar subquery in `VALUES` | our own DF-01 (filed, #27235) and DF-02 (ready to file) |
| DataFusion 55.0.0: `GROUP BY CUBE(a, b)` over constant columns returns the same group twice with split counts when `batch_size` is small and there is more than one partition (the final aggregate is planned as `PartiallySorted` on columns that are constant only before the grouping sets) | fixed on `main` by PR #24422 (19 Aug 2026, after the 55.0.0 release); confirmed by the test-only PR #26898. 564 of 631 plan-variant differences in the 12 Nov DataFusion campaign were this bug |
| DataFusion 55.0.0: `NULL::int[] @> arr` (`array_has_all`) is `true` instead of NULL for a batch in which `arr` is NULL in every row, so the result of a filter after a LEFT JOIN depends on the batch size (0 rows by default, 77 with `batch_size = 2`) | fixed on `main`: `array_has_all_and_any_dispatch` now carries the NULL masks of both arguments into its all-empty branch |
| DataFusion 55.0.0: `UNION` (distinct) over a `STDDEV` result keeps 1 or 2 rows depending on batch size | not a bug: floating-point aggregates differ in the last bit with the order of the rows; the fuzzer no longer compares such queries across plans |
| DuckDB nightly: TLP mismatch for a `SELECT` with `QUALIFY count(*) OVER () = 3` | not a bug: our TLP partitioned the WHERE of a select whose window function sees the filtered rows; fixed in the rewriter |

