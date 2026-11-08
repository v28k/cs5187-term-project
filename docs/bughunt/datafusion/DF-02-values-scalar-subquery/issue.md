**Title:** Scalar subquery in a VALUES row: "Internal error: ScalarSubqueryExpr evaluated before the subquery was executed"

(Form: https://github.com/apache/datafusion/issues/new?template=bug_report.yml — one section per form field.)

**Describe the bug**

A VALUES list whose rows contain an uncorrelated scalar subquery fails with an internal error:

```
Internal error: ScalarSubqueryExpr evaluated before the subquery was executed.
This issue was likely caused by a bug in DataFusion's code. ...
```

The physical planner turns `LogicalPlan::Values` into `MemorySourceConfig::try_new_as_values`, which evaluates every
row expression while the plan is built. A scalar subquery is now a `ScalarSubqueryExpr` whose value is filled in by
`ScalarSubqueryExec` at execution time, so at planning time it has no value yet.

**To Reproduce**

```sql
VALUES ((SELECT 1), 5);

SELECT * FROM (VALUES ((SELECT min(x) FROM (VALUES (1), (2)) AS v(x)), 5)) AS t(a, b);

CREATE TABLE v (a BIGINT, b BIGINT);
INSERT INTO v VALUES ((SELECT 1), 5);
```

All three fail with the internal error above.

**Expected behavior**

`(1, 5)` for the first two queries; the INSERT inserts one row `(1, 5)`.

**Additional context**

Reproduced with `datafusion-cli` built from `main` at bc86321 (57.0.0-dev) and with datafusion-python 55.0.0.
Found with a grammar-based SQL fuzzer.

**Willingness to contribute:** I plan to contribute a fix for this bug independently
