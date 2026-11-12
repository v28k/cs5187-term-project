-- composition of rule kernels L:replace_distinct_aggregate x P:OutputRequirements (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka WHERE (SELECT count(*) FROM (SELECT '2000-01-01'::date AS c0, 'NaN'::text AS c1 UNION SELECT '1999-12-31'::date AS c0, 'abc'::text AS c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka
