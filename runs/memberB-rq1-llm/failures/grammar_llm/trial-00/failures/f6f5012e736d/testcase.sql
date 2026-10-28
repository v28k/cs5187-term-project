-- pgfuzz failure f6f5012e736d (assertion, signature strength: stack)
-- test case 62449 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #1
SELECT JSONB_AGG (('50'::float8 - CASE WHEN TRUE THEN (-1.5)::float8 ELSE (0.5::float8 - (1.0 / 3)::float8) END) ORDER BY ('50'::float8 - CASE WHEN TRUE THEN (-1.5)::float8 ELSE (0.5::float8 - (1.0 / 3)::float8) END)) AS c0, (a1.c1 NOT IN (a1.c1, a1.c1)) AS c1 FROM JSON_TABLE (JSON_QUERY (JSONB_INSERT (JSONB_BUILD_OBJECT ('k', '0'::interval, 'a', JSONB_BUILD_ARRAY (10, (ROW ('44'::int, ARRAY[1]) >= ROW ((-12), '{1,2,3,4}'::int[])))), '{a,0}', '{"k": 1, "a": [1, 2]}'::jsonb), '$.a[1]'), '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a1 GROUP BY GROUPING SETS ((a1.c1), ()) UNION (SELECT JSON_AGG ((-42) ORDER BY (-42) DESC)::jsonb AS c0, TRUE AS c1 FROM ti AS a2 WHERE TRUE UNION SELECT '{"k": 0, "a": [3, 4, 5]}'::jsonb AS c0, FALSE AS c1 FROM t3 AS a3);
