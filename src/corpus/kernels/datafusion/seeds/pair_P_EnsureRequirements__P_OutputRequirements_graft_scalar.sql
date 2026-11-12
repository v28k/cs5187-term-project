-- composition of rule kernels P:EnsureRequirements x P:OutputRequirements (datafusion), template graft_scalar
SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM (SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT 2 AS c0) AS kb) >= 0) AS a1 WHERE a1.c1;
-- pgfuzz:check kernel:graft_scalar SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1
