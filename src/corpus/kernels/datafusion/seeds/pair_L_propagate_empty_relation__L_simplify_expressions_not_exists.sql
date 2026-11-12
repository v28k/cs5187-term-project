-- composition of rule kernels L:propagate_empty_relation x L:simplify_expressions (datafusion), template not_exists
SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka) ELSE 0 END
