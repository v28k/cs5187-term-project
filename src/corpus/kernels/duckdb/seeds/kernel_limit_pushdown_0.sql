-- rule kernel: limit_pushdown (duckdb)
SELECT (SELECT MAX (a1.c0) FROM t4 AS a1 WHERE (EXISTS (SELECT 1::bigint AS c0))) AS c0, '2000-01-01'::date AS c1;
