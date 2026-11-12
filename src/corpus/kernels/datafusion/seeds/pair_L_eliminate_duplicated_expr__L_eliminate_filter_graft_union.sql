-- composition of rule kernels L:eliminate_duplicated_expr x L:eliminate_filter (datafusion), template graft_union
SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM (SELECT * FROM tl UNION ALL SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT 'c4ca4238a0b923820dcc509a6f75849b'::text AS c0 ORDER BY 1, 1) AS kb) < 0) AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE;
-- pgfuzz:check kernel:graft_union SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM tl AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE
