-- rule kernel: L:eliminate_join (datafusion)
WITH cte1 AS (SELECT DISTINCT a2.c0 AS c0, (1.0 / 3)::float8 AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3))) SELECT 1.5::numeric AS c0, TRUE AS c1 FROM t4 AS a3 WHERE (('2024-12-31'::date = '2000-01-01'::date) OR ((ABS (3))::bigint >= LEAST (10::bigint, (SELECT COUNT (*) FROM cte1 AS a4))));
