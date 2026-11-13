-- composition of rule kernels L:eliminate_filter x L:simplify_expressions (datafusion), template not_exists
SELECT count(*) FROM (SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM tl AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM tl AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE) AS ka) ELSE 0 END
