-- pgfuzz failure cde9712bc8db (assertion, signature strength: stack)
-- test case 28873 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #2
SET LOCAL work_mem = '64kB';
SELECT 0.5::float8 AS c0, a2.c0 AS c1 FROM (v0 AS a1 CROSS JOIN JSON_TABLE (JSONB_SET (JSONB_BUILD_OBJECT ('k', 10, 'a', JSONB_BUILD_ARRAY ((-11), (ROW (42.5::numeric, '30'::int) < ROW (42.5::numeric, '8'::int)))), '{a,0}', '{"k": 1, "a": [1, 2]}'::jsonb), '$.a[*]' COLUMNS (c0 FOR ORDINALITY, c1 int PATH '$')) AS a2);
