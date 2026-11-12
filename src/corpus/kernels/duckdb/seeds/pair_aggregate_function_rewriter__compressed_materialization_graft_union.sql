-- composition of rule kernels aggregate_function_rewriter x compressed_materialization (duckdb), template graft_union
SELECT a1.c0 AS c0, a1.c0 AS c1, AVG (41) AS c2, AVG ((-1.5)::float8) AS c3 FROM (SELECT * FROM t0 UNION ALL SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1) AS kb) < 0) AS a1 GROUP BY a1.c0;
-- pgfuzz:check kernel:graft_union SELECT a1.c0 AS c0, a1.c0 AS c1, AVG (41) AS c2, AVG ((-1.5)::float8) AS c3 FROM t0 AS a1 GROUP BY a1.c0
