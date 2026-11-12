-- rule kernel: filter_pushdown (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT []::text[] AS c0, 10.0::float8 AS c1, a1.c3 AS c2 FROM t3 AS a1 WHERE a1.c1 UNION ALL SELECT ARRAY['1'::text] AS c0, 100.0::float8 AS c1, '00:00:00.000001'::interval AS c2;
