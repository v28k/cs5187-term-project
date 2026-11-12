-- rule kernel: in_clause (duckdb)
SELECT a1.c0 AS c0, a1.c1 AS c1, a1.c2 AS c2, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c3 FROM t0 AS a1 GROUP BY a1.c1, a1.c2, a1.c0 HAVING (a1.c2 IN (MAX (a1.c2)));
