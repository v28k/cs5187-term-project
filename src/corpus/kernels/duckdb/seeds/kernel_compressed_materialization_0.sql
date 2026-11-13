-- rule kernel: compressed_materialization (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT 100::bigint AS c0 UNION SELECT 10::bigint AS c0;
