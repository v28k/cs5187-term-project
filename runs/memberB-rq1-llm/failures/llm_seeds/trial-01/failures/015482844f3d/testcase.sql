-- pgfuzz failure 015482844f3d (wrong_result, signature strength: diff)
-- test case 4881 from grammar
-- SQLSTATE -: metamorphic check rls failed: 8 rows vs 8 rows
-- failing statement: #1
SELECT ARRAY_AGG ((SELECT PERCENTILE_DISC (0.5) WITHIN GROUP (ORDER BY a2.c0) FROM tp AS a2) ORDER BY (SELECT PERCENTILE_DISC (0.5) WITHIN GROUP (ORDER BY a2.c0) FROM tp AS a2)) AS c0, '{"k": 1}'::text AS c1 FROM ti AS a1 WHERE GREATEST (TRUE, FALSE) GROUP BY GROUPING SETS ((a1.c0), (a1.c1), ()) UNION SELECT ARRAY_AGG (a3.c0 ORDER BY a3.c0) AS c0, 'é'::text AS c1 FROM tl AS a3 GROUP BY ROLLUP (a3.c1) ORDER BY 2 NULLS LAST;
SELECT MIN ('abc'::text) FILTER (WHERE TRUE) AS c0 FROM t2 AS a1 WHERE (EXISTS (SELECT a2.c0 AS c0, a2.n AS c1, '{1,2,3,4}'::int[] AS c2 FROM v0 AS a2 WHERE FALSE GROUP BY a2.c0, a2.n)) GROUP BY a1.c3, a1.c0 HAVING TRUE ORDER BY 1;
