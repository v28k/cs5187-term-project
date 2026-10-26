-- pgfuzz failure 448f485d72d5 (assertion, signature strength: stack)
-- test case 36154 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #1
SELECT 16 AS c0, (MAX (0.0::float8) OVER (PARTITION BY a1.c2, a1.c2) IN (SELECT '6.333333333333333'::float8 AS c0 FROM tp AS a4 GROUP BY a4.c1, a4.c0)) AS c1, a1.c3 AS c2, (SELECT MIN ('00:00:00.000001'::interval) FROM (SELECT a5.c0 AS c0, '_'::text AS c1, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c2 FROM v0 AS a5) AS a6 WHERE TRUE) AS c3 FROM t4 AS a1 WHERE ((a1.c0 <> ANY (SELECT a2.c0 AS c0 FROM tp AS a2 WHERE FALSE UNION ALL SELECT a1.c0 AS c0 FROM v0 AS a3)) AND FALSE);
SELECT 2 AS c0 FROM t0 AS a1 WHERE (('{NULL,1}'::int[] IS NULL) AND (25 NOT IN (SELECT a2.c0 AS c0 FROM t1 AS a2 WHERE (a2.c2 <> ALL (SELECT a2.c2 AS c0 FROM v0 AS a3 GROUP BY a3.c0 HAVING (a1.c0 BETWEEN '8'::int AND '1'::int))))));
