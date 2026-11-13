> **Do not file: fixed upstream by 57a6875edf (PR #28246, issue #28156). Kept for the record.**

**Title:** INTERNAL Error "Failed to bind column reference" for an outer-join / MERGE condition with two subqueries

**What happens?**

A LEFT/RIGHT JOIN or MERGE condition that contains two subqueries fails with an INTERNAL error when one of them is
a scalar subquery compared with `ANY` over a list that references columns of both join sides:

```
INTERNAL Error: Failed to bind column reference "a" [38.0] (bindings: {#[48.0]})
```

In 1.5.6 these queries were rejected with "Cannot perform non-inner join on subquery!", so this seems to be in the
new support for subqueries in non-inner join conditions (2.0.0). The INNER JOIN form, and the same condition with
the constant `1` instead of `(SELECT 1)`, work.

**To Reproduce**

```sql
CREATE TABLE t (a INTEGER, b BOOLEAN);
CREATE TABLE u (c INTEGER);
INSERT INTO t VALUES (1, true), (6, false);
INSERT INTO u VALUES (1);

SELECT * FROM t LEFT JOIN (SELECT 5 AS x) s ON ((SELECT 1) = ANY ([t.a + s.x]) OR 1 IN (SELECT c FROM u));
-- INTERNAL Error: Failed to bind column reference "a" ...   (expected: (1, true, 5), (6, false, 5))

SELECT * FROM t RIGHT JOIN (SELECT 5 AS x) s ON ((SELECT 1) = ANY ([t.a + s.x]) OR 1 IN (SELECT c FROM u));
-- INTERNAL Error: Failed to bind column reference "x" ...

MERGE INTO t USING (SELECT 5 AS x) s ON ((SELECT 1) = ANY ([t.a + s.x]) OR 1 IN (SELECT c FROM u))
WHEN NOT MATCHED THEN INSERT VALUES (1, true);
-- INTERNAL Error: Failed to bind column reference "x" ...
```

**OS:** Linux x86_64

**DuckDB Version:** 2.0.0 and 2.1.0.dev2610310630 (nightly)

**DuckDB Client:** Python

**Hardware:** x86_64, 4 cores

**Full Name:** Venu Kummari

**Affiliation:** IIT Guwahati

**What is the latest build you tested with?** nightly 2.1.0.dev2610310630

**Did you include all relevant configuration?** Yes

**Did you include all code required to reproduce the issue?** Yes

**Did you include all relevant data sets?** Not applicable - the reproduction does not require a data set
