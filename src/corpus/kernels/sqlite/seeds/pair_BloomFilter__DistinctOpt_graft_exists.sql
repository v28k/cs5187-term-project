-- composition of rule kernels BloomFilter x DistinctOpt (sqlite), template graft_exists
CREATE TABLE t (a,b,c,d);
INSERT INTO t VALUES (1,2,3,4),(2,3,4,5);
SELECT '{"k": 2, "a": [0]}' AS c0 FROM (SELECT * FROM tp WHERE EXISTS (SELECT 1 FROM (SELECT DISTINCT c FROM t) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT DISTINCT c FROM t) AS kb)) AS a1 WHERE ((a1.c1, CASE WHEN FALSE THEN TRUE ELSE (CAST(1 AS INTEGER) IN (SELECT CAST(100 AS INTEGER) AS c0)) END) <> (a1.c1, TRUE)) GROUP BY a1.c0, a1.c1;
-- pgfuzz:check kernel:graft_exists SELECT '{"k": 2, "a": [0]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, CASE WHEN FALSE THEN TRUE ELSE (CAST(1 AS INTEGER) IN (SELECT CAST(100 AS INTEGER) AS c0)) END) <> (a1.c1, TRUE)) GROUP BY a1.c0, a1.c1
