-- composition of rule kernels aggregate_function_rewriter x reorder_filter (duckdb), template graft_scalar
SELECT 2.25::numeric AS c0, '0'::text AS c1, (SELECT COUNT (*) FROM (SELECT * FROM t4 WHERE (SELECT count(*) FROM (SELECT a1.c0 AS c0, a1.c0 AS c1, AVG (41) AS c2, AVG ((-1.5)::float8) AS c3 FROM t0 AS a1 GROUP BY a1.c0) AS kb) >= 0) AS a1 WHERE ((a1.c3 <= 2.25::numeric) OR (a1.c0 IS NULL))) AS c2;
-- pgfuzz:check kernel:graft_scalar SELECT 2.25::numeric AS c0, '0'::text AS c1, (SELECT COUNT (*) FROM t4 AS a1 WHERE ((a1.c3 <= 2.25::numeric) OR (a1.c0 IS NULL))) AS c2
