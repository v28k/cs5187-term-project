-- rule kernel: partitioned_execution (duckdb)
SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1;
