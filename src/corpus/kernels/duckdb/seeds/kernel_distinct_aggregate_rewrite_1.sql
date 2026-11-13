-- rule kernel: distinct_aggregate_rewrite (duckdb)
SELECT '2000-01-01 00:00:00+00'::timestamptz AS c0, 1.5::numeric AS c1, (- CASE WHEN FALSE THEN (SELECT SUM (DISTINCT a2.c1) FROM t2 AS a2) ELSE 2.25::numeric END) AS c2, 10 AS c3 FROM t1 AS a1;
