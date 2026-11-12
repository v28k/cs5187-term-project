-- composition of rule kernels L:eliminate_duplicated_expr x L:simplify_expressions (datafusion), template cte_twice
WITH ka AS (SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1), kb AS (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1) AS ka) + (SELECT count(*) FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS kb)
