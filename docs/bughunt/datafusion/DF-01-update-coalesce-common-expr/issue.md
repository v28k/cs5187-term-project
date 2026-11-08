**Title:** UPDATE / DELETE fail with "No field named __common_expr_1" when SET or WHERE repeats an expression

(Form: https://github.com/apache/datafusion/issues/new?template=bug_report.yml — one section per form field.)

**Describe the bug**

An `UPDATE` or `DELETE` on a `MemTable` fails at planning time with a schema error about an internal column when its
SET expressions or its WHERE clause contain the same expression twice, for example `COALESCE(c0, 0)` on an INT
column (the column is cast to Int64 twice to match the literal):

```
UPDATE operation on table 't'
caused by
Schema error: No field named __common_expr_1.
Valid fields are c0, c1.
```

Common subexpression elimination moves the repeated expression into a projection below the UPDATE's assignment
projection (or below the DELETE's / UPDATE's filter). The physical planner then reads the assignments
(`extract_update_assignments`) and the filters (`extract_dml_filters`) from the plan and hands them to the table
provider, which evaluates them against the table's own schema, where `__common_expr_1` does not exist.

**To Reproduce**

```sql
CREATE TABLE t (c0 INT, c1 VARCHAR);
INSERT INTO t VALUES (1, 'a'), (NULL, 'b');
UPDATE t SET c0 = COALESCE(c0, 0);                                    -- No field named __common_expr_1
UPDATE t SET c1 = 'z' WHERE COALESCE(c0, 0) > 0 AND COALESCE(c0, 0) < 5;  -- No field named __common_expr_N
DELETE FROM t WHERE COALESCE(c0, 0) > 0 AND COALESCE(c0, 0) < 5;          -- same
```

**Expected behavior**

The first UPDATE updates 2 rows, giving `(1, 'a')` and `(0, 'b')`; the second updates 1 row; the DELETE deletes 1
row. The same expressions work in a SELECT, and `COALESCE(c0, CAST(0 AS INT))` (no repeated cast) works.

**Additional context**

Reproduced with `datafusion-cli` built from `main` at bc86321 (57.0.0-dev) and with datafusion-python 55.0.0.
Found with a grammar-based SQL fuzzer.

**Willingness to contribute:** I plan to contribute a fix for this bug independently
