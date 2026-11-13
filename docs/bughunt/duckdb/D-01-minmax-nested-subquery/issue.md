**Title:** min/max over a nested value computed by a subquery fails with "Cannot copy BoundSubqueryExpression" (regression in 2.0.0)

**What happens?**

`min`/`max` (and `min(x, n)`/`max(x, n)`) fail at bind time when the argument is a LIST, STRUCT or ARRAY value
that contains a subquery:

```
Serialization Error: Cannot copy BoundSubqueryExpression
```

This worked in 1.5.6. It looks like it comes from 2ef9f76b2e ("Apply collations to nested values in min/max
aggregates"): `MinMaxUsesCollation` now returns true for every nested type, so `BindMinMax` calls
`arguments[0]->Copy()`, and copying a `BoundSubqueryExpression` throws. `MinMaxNBind` has the same pattern
(5432471e7a). The same error for a VARCHAR argument with a collation (`SET default_collation = 'nocase'`) already
happened in 1.5.6.

**To Reproduce**

```sql
CREATE TABLE a (x INTEGER);
INSERT INTO a VALUES (1), (2);

SELECT min((SELECT [1])) FROM a;                              -- expected [1]
SELECT max((SELECT {'k': x})) FROM a;                         -- expected {'k': 2}
SELECT max((SELECT [x]), 1) FROM a;                           -- expected [[2]]
SELECT min(CASE WHEN EXISTS (SELECT 1) THEN [x] END) FROM a;  -- expected [1]
```

All four return `Serialization Error: Cannot copy BoundSubqueryExpression` on 2.0.0, on the current nightly and on
`main` (d4eea3f208, built from source);
1.5.6 returns the expected values. `arg_min((SELECT [1]), 1)` and `first((SELECT [1]))` work.

**OS:** Linux x86_64

**DuckDB Version:** 2.0.0, 2.1.0.dev2610310630 (nightly) and main d4eea3f208 (v2.1.0-dev82473); 1.5.6 not affected

**DuckDB Client:** Python and CLI

**Hardware:** x86_64, 4 cores

**Full Name:** Venu Kummari

**Affiliation:** IIT Guwahati

**What is the latest build you tested with?** main d4eea3f208 built from source (and nightly 2.1.0.dev2610310630)

**Did you include all relevant configuration?** Yes

**Did you include all code required to reproduce the issue?** Yes

**Did you include all relevant data sets?** Not applicable - the reproduction does not require a data set
