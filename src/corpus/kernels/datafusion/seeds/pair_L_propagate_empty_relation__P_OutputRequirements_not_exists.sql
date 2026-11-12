-- composition of rule kernels L:propagate_empty_relation x P:OutputRequirements (datafusion), template not_exists
SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka) ELSE 0 END
