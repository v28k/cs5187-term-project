-- rule kernel: unused_columns (duckdb)
SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2;
