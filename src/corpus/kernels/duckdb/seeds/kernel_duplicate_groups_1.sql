-- rule kernel: duplicate_groups (duckdb)
SELECT 10::bigint AS c0 EXCEPT SELECT 10::bigint AS c0 FROM t4 AS a1 GROUP BY a1.c1, a1.c0, a1.c3;
