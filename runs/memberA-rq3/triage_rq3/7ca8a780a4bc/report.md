# wrong_result: result differs under plan variant xversion: 0 rows by default, 2 rows with variant

* Oracle: **cross-version**, signature `7ca8a780a4bc`
* Reproduced: 0/3 on ?
* Reduced: 3 -> ? statements, 149 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of 7ca8a780a4bc: wrong_result via cross-version
DELETE FROM tl AS a1 WHERE (CASE WHEN (a1.c1 SIMILAR TO '%(a|b)%') THEN CASE WHEN FALSE THEN '{"k": -1, "a": [1, 2, 3]}'::jsonb ELSE (LEAST ('{"k": 1, "a": [1, 2]}'::jsonb, '{"k": 0, "a": [3, 4, 5]}'::jsonb) -> 1) END ELSE LEAST (COALESCE (JSON_ARRAY ((COALESCE (GREATEST (('abc'::text <= CONCAT_WS ('-', a1.c1, '1999-12-31 23:59:59.999999+05:30'::timestamptz)), FALSE), TRUE) AND (TO_CHAR ('2024-01-01 00:00:00+00'::timestamptz, 'YYYY-MM-DD HH24:MI') BETWEEN a1.c1 AND LOWER ('NaN'::text))), TRUE RETURNING jsonb), CASE WHEN FALSE THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb ELSE '{"k": 2, "a": [0]}'::jsonb END), '{"k": 2, "a": [0]}'::jsonb) END <@ '{"k": 2, "a": [0]}'::jsonb);
DELETE FROM t0 AS a1 USING t4 AS a2 WHERE (((SELECT MAX (ARRAY[1]) FROM t2 AS a3, LATERAL (SELECT '1 year 2 mons 3 days 04:05:06.789'::interval AS c0 ORDER BY 1 LIMIT 2) AS a4))[1 : 2] @> LEAST (ARRAY_POSITIONS (ARRAY[1], 1), COALESCE ((SELECT MIN (a5.c4) FROM t3 AS a5 WHERE CASE a1.c0 WHEN a2.c0 THEN TRUE WHEN a2.c1 THEN FALSE ELSE a5.c1 END), (SELECT MIN ('{NULL,1}'::int[]) FROM t0 AS a6, UNNEST (NULLIF ('{a,b}'::text[], LEAST (COALESCE ('{a,b}'::text[], ARRAY['1'::text]), ARRAY['x'::text, NULL::text]))) AS a7 (c0)))));
SELECT DISTINCT CASE COALESCE ((-0.0)::float8, COALESCE (a1.c2, a1.c2)) WHEN 5e-324::float8 THEN a1.c1 WHEN (SELECT MIN ((-1.5)::float8) FROM tl AS a3 WHERE ('{}'::int[] IS DISTINCT FROM ARRAY[1, 2, 3])) THEN INITCAP ('%'::text) ELSE ' '::text END AS c0, JSONB_TYPEOF ((LEAST ((a2.c0 -> (-1)), a2.c0) #> '{k}')) AS c1 FROM t0 AS a1, JSONB_ARRAY_ELEMENTS (JSONB_BUILD_ARRAY (LOWER ('[1,10)'::int4range), GREATEST (TO_JSONB ('{a,b,c,d}'::text[]), '{"k": -1, "a": [1, 2, 3]}'::jsonb))) AS a2 (c0) ORDER BY 1;
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
