-- composition of rule kernels L:eliminate_filter x L:simplify_expressions (datafusion), template graft_scalar
SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM (SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb) >= 0) AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE;
-- pgfuzz:check kernel:graft_scalar SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM tl AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE
