-- rule kernel: partial_aggregate_pushdown (duckdb)
WITH cte1 AS (SELECT GREATEST ((a1.c1 || MIN (''::text) OVER (PARTITION BY a1.c0)), 'c4ca4238a0b923820dcc509a6f75849b'::text) AS c0 FROM ti AS a1) SELECT 39 AS c0 FROM cte1 AS a2 GROUP BY GROUPING SETS ((a2.c0), ()) EXCEPT ALL SELECT 7 AS c0;
