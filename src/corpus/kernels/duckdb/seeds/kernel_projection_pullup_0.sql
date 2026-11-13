-- rule kernel: projection_pullup (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT []::text[] AS c0, 5e-324::float8 AS c1, '00:00:00.000001'::interval AS c2 UNION ALL SELECT ARRAY['1'::text] AS c0, 10.0::float8 AS c1, MIN ('0'::interval) OVER (PARTITION BY 16) AS c2 FROM v0 AS a1;
