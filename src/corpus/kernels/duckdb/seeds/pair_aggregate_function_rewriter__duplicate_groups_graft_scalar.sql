-- composition of rule kernels aggregate_function_rewriter x duplicate_groups (duckdb), template graft_scalar
SELECT ((COUNT (DISTINCT a1.c1) % 1000)::int - 1) AS c0, a1.c1 AS c1, 'A'::text AS c2, 1::bigint AS c3 FROM (SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT a1.c0 AS c0, a1.c0 AS c1, AVG (41) AS c2, AVG ((-1.5)::float8) AS c3 FROM t0 AS a1 GROUP BY a1.c0) AS kb) >= 0) AS a1 GROUP BY a1.c1;
-- pgfuzz:check kernel:graft_scalar SELECT ((COUNT (DISTINCT a1.c1) % 1000)::int - 1) AS c0, a1.c1 AS c1, 'A'::text AS c2, 1::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1
