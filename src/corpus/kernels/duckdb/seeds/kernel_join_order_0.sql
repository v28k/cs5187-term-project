-- rule kernel: join_order (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT 0 AS c0 UNION SELECT 7 AS c0;
