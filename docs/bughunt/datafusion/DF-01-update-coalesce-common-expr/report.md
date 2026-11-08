# DF-01: `UPDATE t SET c0 = COALESCE(c0, 0)` fails with "No field named __common_expr_1"

| | |
|---|---|
| Status | **candidate: re-run on `main` before filing** (reproduced on the latest release wheel only) |
| Target | Apache DataFusion (https://github.com/apache/datafusion) |
| Kind | valid UPDATE rejected with an internal schema error (an optimizer artefact leaks into DML planning) |
| Affected | datafusion-python 55.0.0 (DataFusion 55). `main` (57.0.0-dev, 9d15cf0) **not tested**: building it was not allowed in our environment |
| Found by | grammar fuzzer, DataFusion target, internal-error oracle (8 Nov 2026) |

## Reproducer

```sql
CREATE TABLE t (c0 INT, c1 VARCHAR);
INSERT INTO t VALUES (1, 'a'), (NULL, 'b');
UPDATE t SET c0 = COALESCE(c0, 0);
```

Actual: `UPDATE operation on table 't' caused by Schema error: No field named __common_expr_1. Valid fields are c0, c1.`
Expected: 2 rows updated (`(1, 'a')`, `(0, 'b')`).

What matters (each checked on 55.0.0): the INT32 column is coerced to INT64 to match the literal, so the rewritten
expression contains `CAST(c0 AS Int64)` twice.
- fails: `COALESCE(c0, 0)`, `COALESCE(c0, c0 + 1)`, `COALESCE(c0, 0) + 1` (c0 INT)
- works: `COALESCE(c0, CAST(0 AS INT))`, `COALESCE(c2, 0)` with c2 BIGINT, `COALESCE(c1, 'z')`, `NULLIF(c0, 1)`,
  `GREATEST(c0, 0)`, `CASE WHEN c0 IS NULL THEN 0 ELSE c0 END`, `c0 * c0`; `SELECT COALESCE(c0, 0) FROM t` works.

## Likely cause

`common_sub_expression_eliminate` extracts the repeated `CAST(t.c0 AS Int64)` of the coerced COALESCE into a
projection column `__common_expr_1`; the UPDATE path then evaluates the assignment expressions against the table
schema (c0, c1), where that column does not exist. (Not verified in the source of `main`.)

## Duplicate search (8 Nov 2026)

`git log` of apache/datafusion main (to 9d15cf0): no commit mentioning UPDATE together with common subexpressions /
`__common_expr`; no `.slt` test with `UPDATE ... SET ... = COALESCE(`. Owner: search
https://github.com/apache/datafusion/issues?q=__common_expr+update before filing.

## Files

`repro.sql`, `update_common_expr.slt` (sqllogictest for `datafusion/sqllogictest/test_files/`), `issue.md`, `steps.md`.
