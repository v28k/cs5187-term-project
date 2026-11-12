-- composition of rule kernels DistinctOpt x ExistsToJoin (sqlite), template graft_exists
CREATE TABLE t (a,b,c,d);
INSERT INTO t VALUES (1,2,3,4),(2,3,4,5);
SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0, '2024-01-01 00:00:00' AS c1 FROM (SELECT * FROM t0 WHERE EXISTS (SELECT 1 FROM (SELECT DISTINCT c FROM t) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT DISTINCT c FROM t) AS kb)) AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0, a2.c0 AS c1, a1.c1 AS c2 FROM t1 AS a2));
-- pgfuzz:check kernel:graft_exists SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0, '2024-01-01 00:00:00' AS c1 FROM t0 AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0, a2.c0 AS c1, a1.c1 AS c2 FROM t1 AS a2))
