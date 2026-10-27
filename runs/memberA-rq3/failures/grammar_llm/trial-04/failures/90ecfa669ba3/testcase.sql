-- pgfuzz failure 90ecfa669ba3 (wrong_result, signature strength: diff)
-- test case 36624 from grammar
-- SQLSTATE -: metamorphic check tlp_where failed: 1 rows vs 1 rows
-- failing statement: #3
ANALYZE t3;
SELECT a1.c0 AS c0, a1.c0 AS c1 FROM t1 AS a1 GROUP BY a1.c3, a1.c0 INTERSECT SELECT '50'::int AS c0, 2 AS c1 FROM (SELECT 100.0::float8 AS c0 FROM tp AS a2 GROUP BY a2.c0) AS a3 WHERE TRUE GROUP BY a3.c0 HAVING (TRUE AND FALSE);
SELECT '7 days'::interval AS c0 FROM t4 AS a1 WHERE ('6.333333333333333'::float8 IN (SELECT (1.0 / 3)::float8 AS c0)) INTERSECT ALL SELECT a2.c3 AS c0 FROM t3 AS a2 GROUP BY a2.c2, a2.c3, a2.c5 ORDER BY 1, 1;
