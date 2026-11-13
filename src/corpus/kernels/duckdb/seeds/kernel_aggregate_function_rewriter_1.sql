-- rule kernel: aggregate_function_rewriter (duckdb)
SELECT a1.c0 AS c0, a1.c0 AS c1, AVG (41) AS c2, AVG ((-1.5)::float8) AS c3 FROM t0 AS a1 GROUP BY a1.c0;
