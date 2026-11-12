-- rule kernel: partitioned_execution (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT ARRAY['1'::text] AS c0, 1.0::float8 AS c1, a1.c3 AS c2 FROM t3 AS a1 UNION ALL SELECT ARRAY['1'::text] AS c0, 0.5::float8 AS c1, '-3 hours'::interval AS c2 ORDER BY 3;
