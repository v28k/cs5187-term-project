-- rule kernel: reorder_filter (duckdb)
SELECT 2.25::numeric AS c0, '0'::text AS c1, (SELECT COUNT (*) FROM t4 AS a1 WHERE ((a1.c3 <= 2.25::numeric) OR (a1.c0 IS NULL))) AS c2;
