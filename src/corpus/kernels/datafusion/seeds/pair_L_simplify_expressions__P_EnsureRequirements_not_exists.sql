-- composition of rule kernels L:simplify_expressions x P:EnsureRequirements (datafusion), template not_exists
SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka) ELSE 0 END
