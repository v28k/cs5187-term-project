-- rule kernel: deliminator (duckdb)
SELECT 'A'::text AS c0 FROM t0 AS a1, LATERAL (SELECT '1999-12-31 23:59:59.999999+05:30'::timestamptz AS c0, a1.c1 AS c1) AS a2 EXCEPT ALL SELECT 'A'::text AS c0;
