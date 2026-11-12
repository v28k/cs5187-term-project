-- composition of rule kernels L:eliminate_duplicated_expr x P:OutputRequirements (datafusion), template product
SELECT count(*) FROM (SELECT 2 AS c0) AS ka CROSS JOIN (SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT 2 AS c0) AS ka) * (SELECT count(*) FROM (SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1) AS kb)
