-- composition of rule kernels compressed_materialization x distinct_aggregate_rewrite (duckdb), template graft_scalar
SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM (SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT ((COUNT (DISTINCT a1.c5) % 1000)::int - 1) AS c0, a1.c5 AS c1, 'A'::text AS c2, 0::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS kb) >= 0) AS a1 GROUP BY a1.c1;
-- pgfuzz:check kernel:graft_scalar SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1
