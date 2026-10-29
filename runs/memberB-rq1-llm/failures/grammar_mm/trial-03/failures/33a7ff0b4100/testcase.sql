-- pgfuzz failure 33a7ff0b4100 (assertion, signature strength: stack)
-- test case 30392 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #1
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) SELECT '{"k": 1, "a": [1, 2]}'::jsonb AS c0, 'A'::text AS c1, TRUE AS c2, CASE JSON_VALUE (JSON_OBJECT ('k' VALUE '-3 hours'::interval RETURNING jsonb), '$.a[*]') WHEN a1.c1 THEN 'ß'::text WHEN 'W'::text THEN CASE WHEN ('{"k": 1, "a": [1, 2]}'::jsonb <@ '{"k": 0, "a": [3, 4, 5]}'::jsonb) THEN ('{"k": 2, "a": [0]}'::jsonb ->> 0) ELSE COALESCE (a1.c1, a1.c1) END ELSE JSON_VALUE (JSON_ARRAY ('0'::int, 100 RETURNING jsonb), '$.a.size()') END AS c3 FROM tp AS a1 WHERE (a1.c0 = ALL (SELECT 10 AS c0 FROM t3 AS a2));
