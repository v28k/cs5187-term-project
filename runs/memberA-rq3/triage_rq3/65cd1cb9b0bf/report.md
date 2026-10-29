# performance: row estimate rises when the WHERE clause is added: 300.0 -> 720.0

* Oracle: **plan-variant**, signature `65cd1cb9b0bf`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 141 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of 65cd1cb9b0bf: performance via plan-variant
SELECT CASE WHEN a2.c1 THEN '{"k": -1, "a": [1, 2, 3]}'::jsonb ELSE (SELECT JSON_AGG ('NaN'::text ORDER BY 'NaN'::text)::jsonb FROM tp AS a5 WHERE a2.c1) END AS c0, a3.c0 AS c1 FROM ((t0 AS a1 JOIN t3 AS a2 ON ((a1.c0 = a2.c0) AND TRUE)) RIGHT JOIN (t2 AS a3 CROSS JOIN ROWS FROM (GENERATE_SERIES (1, 3), UNNEST (ARRAY['x'::text, NULL::text])) AS a4 (c0, c1)) ON ((a1.c0 = a4.c0) AND (a1.c0 = '4'::int))) WHERE a2.c1 ORDER BY 2, 1;
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
