**Title:** `UPDATE t SET c0 = COALESCE(c0, 0)` fails: "No field named __common_expr_1"

**Describe the bug**

An UPDATE whose SET expression contains the same implicit cast twice, e.g. `COALESCE(c0, 0)` on an INT column (the
column is cast to Int64 to match the literal), fails at planning time with a schema error about an internal column:

```
UPDATE operation on table 't' caused by Schema error: No field named __common_expr_1. Valid fields are c0, c1.
```

It looks like common subexpression elimination extracts the repeated `CAST(c0 AS Int64)` into `__common_expr_1`,
which the UPDATE assignment then cannot resolve against the table schema. `COALESCE(c0, CAST(0 AS INT))`,
`COALESCE` on a BIGINT column, `NULLIF(c0, 1)` and `GREATEST(c0, 0)` work; `COALESCE(c0, c0 + 1)` fails too.

**To Reproduce**

```sql
CREATE TABLE t (c0 INT, c1 VARCHAR);
INSERT INTO t VALUES (1, 'a'), (NULL, 'b');
UPDATE t SET c0 = COALESCE(c0, 0);
```

**Expected behavior**

2 rows updated; the table then holds `(1, 'a')` and `(0, 'b')`. The same expression in a SELECT works.

**Additional context**

Found with a grammar-based SQL fuzzer. Reproduced with datafusion-python 55.0.0 (DataFusion 55).
