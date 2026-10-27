-- pgfuzz failure 83bdce4a0403 (assertion, signature strength: stack)
-- test case 24182 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #3
ANALYZE t4;
DELETE FROM ti AS a1 USING t4 AS a2;
SELECT CASE WHEN FALSE THEN 0.5::numeric ELSE CASE WHEN TRUE THEN '1.7142857142857143'::numeric ELSE 0.5::numeric END END AS c0 FROM t3 AS a1 WHERE (a1.c5 IN (SELECT a1.c5 AS c0 FROM v0 AS a2 UNION ALL SELECT 'A'::text AS c0 FROM t0 AS a3 GROUP BY a3.c2, a3.c0, a3.c1 HAVING FALSE)) INTERSECT ALL (SELECT 0.5::numeric AS c0 FROM t0 AS a4 WHERE TRUE GROUP BY a4.c2, a4.c0, a4.c1 UNION ALL SELECT DISTINCT 42.5::numeric AS c0 FROM v0 AS a5 WHERE TRUE);
