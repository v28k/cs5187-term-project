-- composition of rule kernels L:propagate_empty_relation x P:OutputRequirements (datafusion), template graft_scalar
SELECT 'abc'::text AS c0 FROM (SELECT * FROM t1 WHERE (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS kb) >= 0) AS a1 WHERE FALSE;
-- pgfuzz:check kernel:graft_scalar SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE
