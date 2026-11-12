-- composition of rule kernels L:eliminate_filter x L:simplify_expressions (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka WHERE (SELECT count(*) FROM (SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM tl AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka
