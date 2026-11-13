-- composition of rule kernels L:propagate_empty_relation x L:simplify_expressions (datafusion), template graft_scalar
SELECT 'abc'::text AS c0 FROM (SELECT * FROM t1 WHERE (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb) >= 0) AS a1 WHERE FALSE;
-- pgfuzz:check kernel:graft_scalar SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE
