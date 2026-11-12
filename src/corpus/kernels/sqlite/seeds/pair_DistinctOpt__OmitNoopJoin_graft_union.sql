-- composition of rule kernels DistinctOpt x OmitNoopJoin (sqlite), template graft_union
CREATE TABLE t (a,b,c,d);
INSERT INTO t VALUES (1,2,3,4),(2,3,4,5);
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0 FROM (t0 AS a1 LEFT JOIN (SELECT * FROM t1 UNION ALL SELECT * FROM t1 WHERE (SELECT count(*) FROM (SELECT DISTINCT c FROM t) AS kb) < 0) AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) UNION SELECT CAST('[1,10)' AS TEXT) AS c0;
-- pgfuzz:check kernel:graft_union WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0 FROM (t0 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) UNION SELECT CAST('[1,10)' AS TEXT) AS c0
