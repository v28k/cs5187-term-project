-- composition of rule kernels L:eliminate_duplicated_expr x P:join_selection (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT 'c4ca4238a0b923820dcc509a6f75849b'::text AS c0 ORDER BY 1, 1) AS ka WHERE (SELECT count(*) FROM (SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0))) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 'c4ca4238a0b923820dcc509a6f75849b'::text AS c0 ORDER BY 1, 1) AS ka
