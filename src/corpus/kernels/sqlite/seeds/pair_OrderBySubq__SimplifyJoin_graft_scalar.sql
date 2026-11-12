-- composition of rule kernels OrderBySubq x SimplifyJoin (sqlite), template graft_scalar
CREATE TABLE t (x INT);
INSERT INTO t VALUES (1);
SELECT a1.c0 AS c0, CAST(0.5 AS REAL) AS c1, a2.c0 AS c2, '1970-01-01' AS c3 FROM ((SELECT * FROM tp WHERE (SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb) >= 0) AS a1 FULL JOIN t4 AS a2 ON (a1.c0 = a2.c1)) WHERE (a2.c0 > 100);
-- pgfuzz:check kernel:graft_scalar SELECT a1.c0 AS c0, CAST(0.5 AS REAL) AS c1, a2.c0 AS c2, '1970-01-01' AS c3 FROM (tp AS a1 FULL JOIN t4 AS a2 ON (a1.c0 = a2.c1)) WHERE (a2.c0 > 100)
