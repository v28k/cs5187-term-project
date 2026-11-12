-- composition of rule kernels L:eliminate_duplicated_expr x L:optimize_projections (datafusion), template cte_twice
WITH ka AS (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1), kb AS (SELECT 'c4ca4238a0b923820dcc509a6f75849b'::text AS c0 ORDER BY 1, 1) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1) AS ka) + (SELECT count(*) FROM (SELECT 'c4ca4238a0b923820dcc509a6f75849b'::text AS c0 ORDER BY 1, 1) AS kb)
