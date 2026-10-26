-- pgfuzz failure cc7181e74014 (assertion, signature strength: stack)
-- test case 30401 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #2
SELECT MAX (UPPER ('(,5]'::int4range)) OVER (PARTITION BY (16)::numeric, '_'::text) AS c0 FROM UNNEST ('{a,b}'::text[]) AS a1 (c0) EXCEPT SELECT a3.c0 AS c0 FROM (t1 AS a2 JOIN v0 AS a3 ON (a2.c0 = a3.c0));
SELECT '1 day'::interval AS c0 FROM (JSON_TABLE (CASE WHEN (ROW (500, 10::bigint) <= ROW ((-42), (((100::bigint % 1000) << 1) + 1::bigint))) THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb ELSE '{"k": 0, "a": [3, 4, 5]}'::jsonb END, '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a1 JOIN GENERATE_SERIES (3, 2) AS a2 (c0) ON (a1.c0 = a2.c0)) HAVING (((PERCENTILE_DISC (0) WITHIN GROUP (ORDER BY a2.c0 DESC) % 100) * (((- COUNT (DISTINCT '{NULL,1}'::int[])) % 1000)::int % 100)) IN (SELECT 0 AS c0 FROM t3 AS a3, LATERAL (SELECT ABS (a3.c0) AS c0, (1.5::numeric - 2.25::numeric) AS c1, a3.c4 AS c2) AS a4)) ORDER BY 1, 1 ASC;
