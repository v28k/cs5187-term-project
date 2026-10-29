# wrong_result: result differs under plan variant parallel: 1 rows by default, 1 rows with variant

* Oracle: **plan-variant**, signature `2fddf94021a5`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 616 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of 2fddf94021a5: wrong_result via plan-variant
-- default plan:
SELECT ((CASE WHEN (('2024-01-01 00:00:00+00'::timestamptz - '175:00:00'::interval) <> '2000-01-01 00:00:00+00'::timestamptz) THEN CASE WHEN FALSE THEN ARRAY[1, 2, 3] ELSE ARRAY[33, GREATEST ('7'::int, 10)] END ELSE COALESCE ('{1,2,3,4}'::int[], LEAST ('{}'::int[], '{1,2,3,4}'::int[])) END = (SELECT MAX ('{1,2,3}'::int[]) FROM tp AS a8 WHERE FALSE)) AND (SELECT BOOL_AND (NULL::boolean) FROM tp AS a9 WHERE TRUE)) AS c0, MODE () WITHIN GROUP (ORDER BY ((COALESCE (JUSTIFY_HOURS (a3.c3), a3.c3) - a3.c3) * 1)) AS c1, MODE () WITHIN GROUP (ORDER BY COALESCE (LEAST (CBRT ((SQRT (ABS ('60'::float8)) + CASE ((100::bigint - NULL::bigint) - 10::bigint) WHEN (NULL::bigint - NULL::bigint) THEN '67.66666666666667'::float8 WHEN NULL::bigint THEN '60'::float8 ELSE CASE '\\'::text WHEN a2.c1 THEN NULL::float8 WHEN ''::text THEN 0.5::float8 ELSE ('-2.5'::float8 + 1.0::float8) END END)), ('-Infinity'::float8 + 10.0::float8)), LEAST ((1.0 / 3)::float8, (-0.0)::float8))) AS c2, 'M'::text AS c3 FROM ((tp AS a1 FULL JOIN tp AS a2 ON (a1.c1 = a2.c1)) JOIN t3 AS a3 ON (a1.c0 = a3.c0)) WHERE GREATEST ((((SELECT MAX (a4.c1) FROM tp AS a4 WHERE a3.c1) LIKE 'A_C%'::text) AND CASE WHEN ((NULL::jsonb ? 'a') AND a3.c1) THEN (a3.c1 AND TRUE) ELSE (NOT EXISTS (SELECT CASE WHEN TRUE THEN 'epoch'::timestamptz ELSE '2024-02-29 12:34:56+00'::timestamptz END AS c0)) END), (NOT ((CASE '23'::int WHEN (a2.c0 + a1.c0) THEN 1000::bigint WHEN a3.c0 THEN CASE WHEN a3.c1 THEN CASE WHEN a3.c1 THEN (a1.c0)::bigint ELSE COALESCE (NULL::bigint, CASE 7 WHEN a3.c0 THEN '1'::bigint WHEN a2.c0 THEN 10::bigint ELSE NULL::bigint END) END ELSE (((a3.c0)::bigint - CASE WHEN a3.c1 THEN (-1)::bigint ELSE 1000::bigint END) / NULLIF ((- CASE WHEN a3.c1 THEN NULL::bigint ELSE NULL::bigint END), 0)) END ELSE (10::bigint - 10::bigint) END - '27'::bigint) = ANY (SELECT ('201'::int)::bigint AS c0 FROM ti AS a5 UNION ALL SELECT 100::bigint AS c0 FROM ti AS a6, (VALUES (1, 'a'::text), (2, NULL::text), (NULL::int, 'c'::text)) AS a7 (c0, c1) WHERE TRUE))));
-- plan variant parallel (must return the same rows):
SET debug_parallel_query = 'on';
SET parallel_setup_cost = '0';
SET parallel_tuple_cost = '0';
SET min_parallel_table_scan_size = '0';
SET min_parallel_index_scan_size = '0';
SET max_parallel_workers_per_gather = '4';
SET parallel_leader_participation = 'off';
SELECT ((CASE WHEN (('2024-01-01 00:00:00+00'::timestamptz - '175:00:00'::interval) <> '2000-01-01 00:00:00+00'::timestamptz) THEN CASE WHEN FALSE THEN ARRAY[1, 2, 3] ELSE ARRAY[33, GREATEST ('7'::int, 10)] END ELSE COALESCE ('{1,2,3,4}'::int[], LEAST ('{}'::int[], '{1,2,3,4}'::int[])) END = (SELECT MAX ('{1,2,3}'::int[]) FROM tp AS a8 WHERE FALSE)) AND (SELECT BOOL_AND (NULL::boolean) FROM tp AS a9 WHERE TRUE)) AS c0, MODE () WITHIN GROUP (ORDER BY ((COALESCE (JUSTIFY_HOURS (a3.c3), a3.c3) - a3.c3) * 1)) AS c1, MODE () WITHIN GROUP (ORDER BY COALESCE (LEAST (CBRT ((SQRT (ABS ('60'::float8)) + CASE ((100::bigint - NULL::bigint) - 10::bigint) WHEN (NULL::bigint - NULL::bigint) THEN '67.66666666666667'::float8 WHEN NULL::bigint THEN '60'::float8 ELSE CASE '\\'::text WHEN a2.c1 THEN NULL::float8 WHEN ''::text THEN 0.5::float8 ELSE ('-2.5'::float8 + 1.0::float8) END END)), ('-Infinity'::float8 + 10.0::float8)), LEAST ((1.0 / 3)::float8, (-0.0)::float8))) AS c2, 'M'::text AS c3 FROM ((tp AS a1 FULL JOIN tp AS a2 ON (a1.c1 = a2.c1)) JOIN t3 AS a3 ON (a1.c0 = a3.c0)) WHERE GREATEST ((((SELECT MAX (a4.c1) FROM tp AS a4 WHERE a3.c1) LIKE 'A_C%'::text) AND CASE WHEN ((NULL::jsonb ? 'a') AND a3.c1) THEN (a3.c1 AND TRUE) ELSE (NOT EXISTS (SELECT CASE WHEN TRUE THEN 'epoch'::timestamptz ELSE '2024-02-29 12:34:56+00'::timestamptz END AS c0)) END), (NOT ((CASE '23'::int WHEN (a2.c0 + a1.c0) THEN 1000::bigint WHEN a3.c0 THEN CASE WHEN a3.c1 THEN CASE WHEN a3.c1 THEN (a1.c0)::bigint ELSE COALESCE (NULL::bigint, CASE 7 WHEN a3.c0 THEN '1'::bigint WHEN a2.c0 THEN 10::bigint ELSE NULL::bigint END) END ELSE (((a3.c0)::bigint - CASE WHEN a3.c1 THEN (-1)::bigint ELSE 1000::bigint END) / NULLIF ((- CASE WHEN a3.c1 THEN NULL::bigint ELSE NULL::bigint END), 0)) END ELSE (10::bigint - 10::bigint) END - '27'::bigint) = ANY (SELECT ('201'::int)::bigint AS c0 FROM ti AS a5 UNION ALL SELECT 100::bigint AS c0 FROM ti AS a6, (VALUES (1, 'a'::text), (2, NULL::text), (NULL::int, 'c'::text)) AS a7 (c0, c1) WHERE TRUE))));
RESET debug_parallel_query;
RESET parallel_setup_cost;
RESET parallel_tuple_cost;
RESET min_parallel_table_scan_size;
RESET min_parallel_index_scan_size;
RESET max_parallel_workers_per_gather;
RESET parallel_leader_participation;
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
