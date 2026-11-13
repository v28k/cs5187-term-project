-- composition of rule kernels L:simplify_expressions x P:OutputRequirements (datafusion), template product
SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka CROSS JOIN (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka) * (SELECT count(*) FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS kb)
