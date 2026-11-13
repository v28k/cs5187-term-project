-- composition of rule kernels L:optimize_projections x L:simplify_expressions (datafusion), template not_exists
SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka) ELSE 0 END
