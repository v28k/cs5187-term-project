-- rule kernel: filter_pushdown (duckdb)
SELECT '2024-01-01'::date AS c0, (MAX ('1999-12-31 23:59:59.999999+05:30'::timestamptz) OVER (PARTITION BY '2000-01-01 00:00:00+00'::timestamptz) + '00:00:00.000001'::interval) AS c1 FROM t1 AS a1 WHERE NULLIF ((NULL::int < 2), FALSE);
