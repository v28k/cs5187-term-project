# wrong_result: result differs under plan variant parallel: 3 rows by default, 3 rows with variant

* Oracle: **plan-variant**, signature `485efe9af4d4`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 534 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of 485efe9af4d4: wrong_result via plan-variant
-- default plan:
VALUES ((-0.0)::float8, ((SELECT REGR_SLOPE ('50'::float8, '66.66666666666667'::float8) FROM tl AS a1 WHERE TRUE) - (CASE WHEN ('99'::text !~ '[0-9]{2}') THEN (0.5::float8 + 5e-324::float8) ELSE ('31'::int)::float8 END + FLOOR (NULLIF (1.0::float8, '60'::float8)))), COALESCE ((ARRAY_APPEND (LEAST ('{}'::int[], ARRAY[1, 2, 3]), (7 + LENGTH (JSON_VALUE ('{"k": 0, "a": [3, 4, 5]}'::jsonb, '$.a[*]')))))[2], LENGTH (CONCAT (('2024-01-06 15:00:00+00'::timestamptz IS NOT NULL), LEAST (16, '80'::int))))), (CASE WHEN (GREATEST (TO_CHAR (42.5::numeric, 'FM999990.00'), REPLACE (SPLIT_PART (COALESCE ('A'::text, ('{NULL}'::int[])::text), ',', (-1)), REPLACE ((TO_CHAR (NULL::timestamptz, 'YYYY-MM-DD HH24:MI') || '_'::text), 'é'::text, JSON_VALUE ('{"k": 0, "a": [3, 4, 5]}'::jsonb, '$.a[last]')), 'Z'::text)) IS NOT DISTINCT FROM CASE (16 % NULLIF (LENGTH ((('x'::text || '99'::text) || 'NaN'::text)), 0)) WHEN (-1) THEN SPLIT_PART (''::text, ',', 2) WHEN (COALESCE (CASE WHEN ('16x'::text = 'ß'::text) THEN ASCII ('NaN'::text) ELSE '-1'::int END, '31'::int) + (NULL::int + COALESCE ((-2147483648), CASE CASE WHEN (2.25::numeric IN (0.0::numeric)) THEN 10 ELSE 7 END WHEN ('-infinity'::date - 'infinity'::date) THEN LEAST ((-42), 500) WHEN 2 THEN 100 ELSE '6'::int END))) THEN SUBSTR ('é'::text, '50'::int) ELSE 'abc'::text END) THEN GREATEST ((100.0::float8 - (- 100.0::float8)), (CASE WHEN ('{"k": -1, "a": [1, 2, 3]}'::jsonb @? '$.a[last]') THEN (-1) ELSE 2 END)::float8) ELSE '50'::float8 END, 'Infinity'::float8, COALESCE (1, ABS (GREATEST (LENGTH ('0'::text), LENGTH ('%'::text))))), (0.0::float8, (COALESCE (10.0::float8, (COALESCE (100.0::float8, CASE WHEN (('{"k": -1, "a": [1, 2, 3]}'::jsonb @? '$.a.size()') OR (ARRAY['x'::text, NULL::text] >= '{NULL}'::text[])) THEN 0.5::float8 ELSE 100.0::float8 END) - 0.0::float8)) - '-Infinity'::float8), 7);
-- plan variant parallel (must return the same rows):
SET debug_parallel_query = 'on';
SET parallel_setup_cost = '0';
SET parallel_tuple_cost = '0';
SET min_parallel_table_scan_size = '0';
SET min_parallel_index_scan_size = '0';
SET max_parallel_workers_per_gather = '4';
SET parallel_leader_participation = 'off';
VALUES ((-0.0)::float8, ((SELECT REGR_SLOPE ('50'::float8, '66.66666666666667'::float8) FROM tl AS a1 WHERE TRUE) - (CASE WHEN ('99'::text !~ '[0-9]{2}') THEN (0.5::float8 + 5e-324::float8) ELSE ('31'::int)::float8 END + FLOOR (NULLIF (1.0::float8, '60'::float8)))), COALESCE ((ARRAY_APPEND (LEAST ('{}'::int[], ARRAY[1, 2, 3]), (7 + LENGTH (JSON_VALUE ('{"k": 0, "a": [3, 4, 5]}'::jsonb, '$.a[*]')))))[2], LENGTH (CONCAT (('2024-01-06 15:00:00+00'::timestamptz IS NOT NULL), LEAST (16, '80'::int))))), (CASE WHEN (GREATEST (TO_CHAR (42.5::numeric, 'FM999990.00'), REPLACE (SPLIT_PART (COALESCE ('A'::text, ('{NULL}'::int[])::text), ',', (-1)), REPLACE ((TO_CHAR (NULL::timestamptz, 'YYYY-MM-DD HH24:MI') || '_'::text), 'é'::text, JSON_VALUE ('{"k": 0, "a": [3, 4, 5]}'::jsonb, '$.a[last]')), 'Z'::text)) IS NOT DISTINCT FROM CASE (16 % NULLIF (LENGTH ((('x'::text || '99'::text) || 'NaN'::text)), 0)) WHEN (-1) THEN SPLIT_PART (''::text, ',', 2) WHEN (COALESCE (CASE WHEN ('16x'::text = 'ß'::text) THEN ASCII ('NaN'::text) ELSE '-1'::int END, '31'::int) + (NULL::int + COALESCE ((-2147483648), CASE CASE WHEN (2.25::numeric IN (0.0::numeric)) THEN 10 ELSE 7 END WHEN ('-infinity'::date - 'infinity'::date) THEN LEAST ((-42), 500) WHEN 2 THEN 100 ELSE '6'::int END))) THEN SUBSTR ('é'::text, '50'::int) ELSE 'abc'::text END) THEN GREATEST ((100.0::float8 - (- 100.0::float8)), (CASE WHEN ('{"k": -1, "a": [1, 2, 3]}'::jsonb @? '$.a[last]') THEN (-1) ELSE 2 END)::float8) ELSE '50'::float8 END, 'Infinity'::float8, COALESCE (1, ABS (GREATEST (LENGTH ('0'::text), LENGTH ('%'::text))))), (0.0::float8, (COALESCE (10.0::float8, (COALESCE (100.0::float8, CASE WHEN (('{"k": -1, "a": [1, 2, 3]}'::jsonb @? '$.a.size()') OR (ARRAY['x'::text, NULL::text] >= '{NULL}'::text[])) THEN 0.5::float8 ELSE 100.0::float8 END) - 0.0::float8)) - '-Infinity'::float8), 7);
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
