-- composition of rule kernels common_aggregate x partitioned_execution (duckdb), template graft_scalar
SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM (SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT a1.c0 AS c0, a1.c0 AS c1 FROM t3 AS a1 WHERE (2 > ALL (SELECT a1.c0 AS c0)) INTERSECT (SELECT 17 AS c0, 10 AS c1 UNION SELECT 22 AS c0, 1 AS c1)) AS kb) >= 0) AS a1;
-- pgfuzz:check kernel:graft_scalar SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1
