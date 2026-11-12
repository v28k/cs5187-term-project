-- rule kernel: aggregate_function_rewriter (duckdb)
SELECT (NULLIF (((LIST_SUM (LIST (35 ORDER BY 35)))::int % NULLIF (500, 0)), (-42)) + (-10)) AS c0 FROM t2 AS a1 GROUP BY GROUPING SETS ((a1.c1), (a1.c2), ());
