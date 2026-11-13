-- composition of rule kernels L:eliminate_duplicated_expr x L:optimize_projections (datafusion), template not_exists
SELECT count(*) FROM (SELECT 'c4ca4238a0b923820dcc509a6f75849b'::text AS c0 ORDER BY 1, 1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT 'c4ca4238a0b923820dcc509a6f75849b'::text AS c0 ORDER BY 1, 1) AS ka) ELSE 0 END
