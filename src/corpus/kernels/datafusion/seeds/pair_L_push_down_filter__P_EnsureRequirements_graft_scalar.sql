-- composition of rule kernels L:push_down_filter x P:EnsureRequirements (datafusion), template graft_scalar
SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM (SELECT * FROM t3 WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT ' '::text AS c0, 3 AS c1 ORDER BY 1) AS kb) >= 0) AS a1 WHERE a1.c1;
-- pgfuzz:check kernel:graft_scalar SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1
