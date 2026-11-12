-- composition of rule kernels compressed_materialization x partitioned_execution (duckdb), template graft_union
SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM (SELECT * FROM tl UNION ALL SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1) AS kb) < 0) AS a1;
-- pgfuzz:check kernel:graft_union SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1
