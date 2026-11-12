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
