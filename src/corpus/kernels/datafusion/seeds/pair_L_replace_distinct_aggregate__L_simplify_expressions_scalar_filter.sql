-- composition of rule kernels L:replace_distinct_aggregate x L:simplify_expressions (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka WHERE (SELECT count(*) FROM (SELECT '2000-01-01'::date AS c0, 'NaN'::text AS c1 UNION SELECT '1999-12-31'::date AS c0, 'abc'::text AS c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka
