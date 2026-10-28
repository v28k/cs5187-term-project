-- pgfuzz failure ec8b42ef87ac (assertion, signature strength: stack)
-- test case 53893 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #1
SELECT (-12) AS c0, MIN (a1.c1) FILTER (WHERE CASE WHEN CASE WHEN FALSE THEN FALSE ELSE (('21'::int = 5) OR FALSE) END THEN TRUE ELSE ('24'::text IS NOT JSON) END) AS c1 FROM JSON_TABLE (JSON_QUERY (JSONB_INSERT (JSONB_BUILD_OBJECT ('k', '0'::interval, 'a', JSONB_BUILD_ARRAY (10, (ROW ((7 + 42), ARRAY[1]) >= ROW ((-12), '{1,2,3,4}'::int[])))), '{a,0}', '{"k": 1, "a": [1, 2]}'::jsonb), '$.a[1]'), '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a1 GROUP BY GROUPING SETS ((a1.c1), ());
