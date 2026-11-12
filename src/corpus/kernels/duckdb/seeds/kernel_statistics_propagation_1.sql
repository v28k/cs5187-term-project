-- rule kernel: statistics_propagation (duckdb)
SELECT 20 AS c0, a1.c5 AS c1, 'A'::text AS c2, 1000::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5;
