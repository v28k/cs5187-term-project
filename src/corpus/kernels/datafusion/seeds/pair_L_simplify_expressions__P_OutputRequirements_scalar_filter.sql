-- composition of rule kernels L:simplify_expressions x P:OutputRequirements (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS ka WHERE (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS ka
