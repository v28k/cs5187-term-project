-- composition of rule kernels L:eliminate_duplicated_expr x P:EnsureRequirements (datafusion), template graft_scalar
SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM (SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT 'c4ca4238a0b923820dcc509a6f75849b'::text AS c0 ORDER BY 1, 1) AS kb) >= 0) AS a1 WHERE a1.c1;
-- pgfuzz:check kernel:graft_scalar SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1
