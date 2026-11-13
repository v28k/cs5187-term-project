-- composition of rule kernels L:eliminate_filter x P:ProjectionPushdown (datafusion), template product
SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka CROSS JOIN (SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM tl AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka) * (SELECT count(*) FROM (SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM tl AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE) AS kb)
