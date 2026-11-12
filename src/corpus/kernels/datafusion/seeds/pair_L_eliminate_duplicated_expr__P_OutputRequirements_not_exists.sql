-- composition of rule kernels L:eliminate_duplicated_expr x P:OutputRequirements (datafusion), template not_exists
SELECT count(*) FROM (SELECT 2 AS c0) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT 2 AS c0) AS ka) ELSE 0 END
