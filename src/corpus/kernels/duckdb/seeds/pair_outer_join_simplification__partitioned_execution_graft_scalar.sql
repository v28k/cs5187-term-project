-- composition of rule kernels outer_join_simplification x partitioned_execution (duckdb), template graft_scalar
SELECT 0 AS c0 FROM (tl AS a1 JOIN (t1 AS a2 FULL JOIN (SELECT * FROM v0 WHERE (SELECT count(*) FROM (SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1) AS kb) >= 0) AS a3 ON (a2.c1 = a3.c0)) ON ((a1.c0 = a3.c0) AND TRUE));
-- pgfuzz:check kernel:graft_scalar SELECT 0 AS c0 FROM (tl AS a1 JOIN (t1 AS a2 FULL JOIN v0 AS a3 ON (a2.c1 = a3.c0)) ON ((a1.c0 = a3.c0) AND TRUE))
