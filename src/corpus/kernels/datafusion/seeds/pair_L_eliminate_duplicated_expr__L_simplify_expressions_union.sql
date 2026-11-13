-- composition of rule kernels L:eliminate_duplicated_expr x L:simplify_expressions (datafusion), template union
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS ka UNION ALL SELECT 2 AS k FROM (SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS ka) + (SELECT count(*) FROM (SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1) AS kb)
