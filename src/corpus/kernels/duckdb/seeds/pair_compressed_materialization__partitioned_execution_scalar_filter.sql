-- composition of rule kernels compressed_materialization x partitioned_execution (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1) AS ka WHERE (SELECT count(*) FROM (SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1) AS ka
