# wrong_result: result differs under plan variant xversion: 168 rows by default, 166 rows with variant

* Oracle: **cross-version**, signature `dd35fab1c86e`
* Reproduced: 0/3 on ?
* Reduced: 5 -> ? statements, 125 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of dd35fab1c86e: wrong_result via cross-version
CREATE VIEW n1 AS SELECT LAG (a1.c0) OVER (PARTITION BY a2.c0 ORDER BY 1::bigint DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS c0, ('A'::text || '[1,10)'::text) AS c1, '[1,10)'::text AS c2 FROM (ti AS a1 FULL JOIN t3 AS a2 ON (a1.c1 = a2.c5));
CREATE STATISTICS (MCV) ON c3, c2 FROM t1;
ANALYZE t1;
SELECT (((MIN (a1.c0) - ASCII (MD5 ('{"k": 1}'::text))) % 100) * (CASE WHEN (FALSE AND (ARRAY_LENGTH (ARRAY['1'::text], 1) IS NULL)) THEN (2 - COALESCE (7, (7 % NULLIF (15, 0)))) ELSE (ARRAY_POSITIONS ('{NULL,1}'::int[], 100))[5] END % 100)) AS c0, RANGE_INTERSECT_AGG (COALESCE ('[1,10)'::int4range, 'empty'::int4range)) AS c1, (LOWER (STRING_AGG (DISTINCT a2.c1, ',')))::text AS c2 FROM tp AS a1, ROWS FROM (GENERATE_SERIES (1, 3), UNNEST ('{a,b,c,d}'::text[])) AS a2 (c0, c1) GROUP BY GROUPING SETS ((a2.c1), (a1.c1), ());
SELECT ''::text AS c0 FROM ((t1 AS a1 LEFT OUTER JOIN tl AS a2 ON (a1.c1 = a2.c0)) FULL JOIN (t1 AS a3 FULL JOIN n1 AS a4 ON (a3.c1 = a4.c0)) ON (a1.c1 = a4.c0)) WHERE GREATEST (CASE WHEN (SELECT BOOL_OR (TRUE) FROM v0 AS a5 WHERE TRUE) THEN (a1.c2 <> a1.c2) ELSE ((' '::text <> a4.c2) AND ((a1.c1)::bigint > 100::bigint)) END, TRUE) ORDER BY 1 NULLS LAST;
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
