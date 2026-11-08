**Title:** Scalar subquery in a VALUES row: "Internal error: ScalarSubqueryExpr evaluated before the subquery was executed"

**Describe the bug**

A scalar subquery inside a VALUES list fails with an internal error:

```
Internal error: ScalarSubqueryExpr evaluated before the subquery was executed.
This issue was likely caused by a bug in DataFusion's code.
```

**To Reproduce**

```sql
VALUES ((SELECT 1), 5);
SELECT * FROM (VALUES ((SELECT min(x) FROM (VALUES (1), (2)) AS v(x)), 5)) AS t(a, b);
```

**Expected behavior**

One row `(1, 5)` for both statements.

**Additional context**

Found with a grammar-based SQL fuzzer; reproduced with datafusion-python 55.0.0 (DataFusion 55).
