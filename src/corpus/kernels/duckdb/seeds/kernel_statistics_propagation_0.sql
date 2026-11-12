-- rule kernel: statistics_propagation (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT 100 AS c0, 16 AS c1 UNION SELECT 27 AS c0, 17 AS c1;
