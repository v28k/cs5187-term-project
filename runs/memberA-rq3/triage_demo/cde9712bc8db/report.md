# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `cde9712bc8db`
* Reproduced: 3/3 on 20devel
* Reduced: 3 -> 1 statements, 572 -> 116 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of cde9712bc8db: assertion via assertion
SELECT CASE CASE WHEN NULL THEN NULL ELSE (SELECT MAX ('{NULL}'::text[]) FROM JSON_TABLE (CASE WHEN (ROW (10.0::numeric, 10) >= ROW (0.0::numeric, 1) IS FALSE) THEN '{"k": -1, "a": [1, 2, 3]}'::jsonb ELSE '{"k": 1, "a": [1, 2]}'::jsonb END, '$.a[*]' COLUMNS ( c1 int PATH '$')) AS a6) END WHEN NULL THEN NULL WHEN MAX ('{a,b,c,d}'::text[]) OVER (PARTITION BY '{1,2,3}'::int[]) THEN NULL ELSE '{NULL,1}'::int[] END AS c0 FROM (SELECT a1.c0 AS c0 FROM t0 AS a1) AS a2;
```

## Assertion

`TRAP: failed Assert("list_length(rcexpr->inputcollids) == nopers"), File: "execExpr.c", Line: 2078`

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
