-- composition of rule kernels DistinctOpt x ExistsToJoin (sqlite), template exists
CREATE TABLE t (a,b,c,d);
INSERT INTO t VALUES (1,2,3,4),(2,3,4,5);
SELECT count(*) FROM (SELECT DISTINCT c FROM t) AS ka WHERE EXISTS (SELECT 1 FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0, '2024-01-01 00:00:00' AS c1 FROM t0 AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0, a2.c0 AS c1, a1.c1 AS c2 FROM t1 AS a2))) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0, '2024-01-01 00:00:00' AS c1 FROM t0 AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0, a2.c0 AS c1, a1.c1 AS c2 FROM t1 AS a2))) AS kb) > 0 THEN (SELECT count(*) FROM (SELECT DISTINCT c FROM t) AS ka) ELSE 0 END
