-- pgfuzz failure a819a7520c99 (wrong_result, signature strength: diff)
-- test case 20655 from grammar
-- SQLSTATE -: metamorphic check expr:llm_nullif_null_reduction failed: 46 rows vs 46 rows
-- failing statement: #4
ALTER TABLE ti SET (fillfactor = 10);
INSERT INTO t2 AS a1 (c1) VALUES ((ABS (1.5::numeric) % 1000)) ON CONFLICT DO NOTHING;
SELECT ARRAY[0, a1.c0, a1.c0] AS c0, a1.c0 AS c1, a1.c1 AS c2 FROM (VALUES (1, 'a'::text), (2, NULL::text), (NULL::int, 'c'::text)) AS a1 (c0, c1) WHERE ((5e-324::float8 >= ANY (SELECT '60'::float8 AS c0 FROM ti AS a2 WHERE FALSE)) OR FALSE) GROUP BY ROLLUP (a1.c1, a1.c0) UNION ALL SELECT '{}'::int[] AS c0, MIN ((JSONB_BUILD_OBJECT ('k', a3.c0) ->> 'k')::int) AS c1, ('{"k": 0, "a": [3, 4, 5]}'::jsonb ->> 1) AS c2 FROM t0 AS a3 HAVING (9223372036854775807::bigint NOT IN ((-1)::bigint));
SELECT UPPER (LEFT ('é'::text, 3)) AS c0, 10::bigint AS c1 FROM ti AS a1 EXCEPT ALL SELECT CONCAT_WS ('-', (1.0 / 3)::float8, a2.c0) AS c0, (('8'::bigint % 1000) * (1000::bigint % 1000)) AS c1 FROM t3 AS a2;
