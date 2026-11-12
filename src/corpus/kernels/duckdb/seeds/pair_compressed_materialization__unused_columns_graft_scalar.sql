-- composition of rule kernels compressed_materialization x unused_columns (duckdb), template graft_scalar
SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM (SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS kb) >= 0) AS a1 GROUP BY a1.c1;
-- pgfuzz:check kernel:graft_scalar SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1
