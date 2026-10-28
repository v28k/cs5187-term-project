-- pgfuzz failure 381a793a6668 (assertion, signature strength: stack)
-- test case 10102 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #4
ANALYZE ti;
DELETE FROM t4 AS a1 WHERE (a1.c2 ^@ '99'::text);
SELECT JUSTIFY_HOURS ('-3 hours'::interval) AS c0, a1.c0 AS c1 FROM t4 AS a1;
SELECT '1999-12-31'::date AS c0, ARRAY[1, 2, 3] AS c1 FROM JSON_TABLE (CASE WHEN (ROW ('[0,0]'::int4range, 500) < ROW (INT4RANGE (LEAST (48, 0), GREATEST (31, 0)), '15'::int)) THEN (SELECT JSON_AGG (int4range(2, 40) ORDER BY int4range(2, 40) DESC)::jsonb FROM t0 AS a1 WHERE TRUE) ELSE '{"k": 2, "a": [0]}'::jsonb END, '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a2 ORDER BY 2 DESC NULLS LAST;
