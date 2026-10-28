-- pgfuzz failure ec8b42ef87ac (assertion, signature strength: stack)
-- test case 30781 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #1
SELECT LEAST (100.0::float8, 100.0::float8) AS c0 FROM JSON_TABLE (JSON_ARRAY ((ROW (33, ((500)::numeric / NULLIF (COALESCE (1.5::numeric, 42.5::numeric), 0))) <= ROW (LENGTH ('abc'::text), GREATEST ('1.1428571428571428'::numeric, CASE WHEN FALSE THEN 2.25::numeric ELSE 1.5::numeric END))), (JUSTIFY_HOURS ('00:00:00.000001'::interval) = (('2024-02-29 12:34:56+00'::timestamptz - '1999-12-31 23:59:59.999999+05:30'::timestamptz) * (-1))) RETURNING jsonb), '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a1 WHERE ('{"k": 1}'::text = a1.c1) GROUP BY a1.c0 HAVING BOOL_AND (FALSE) UNION ALL SELECT CBRT ((1.0 / 3)::float8) AS c0 FROM t1 AS a2, JSON_TABLE ('{"k": 2, "a": [0]}'::jsonb, '$.a[*]' COLUMNS (c0 FOR ORDINALITY, c1 int PATH '$')) AS a3 GROUP BY a3.c0, a2.c1, a2.c3;
