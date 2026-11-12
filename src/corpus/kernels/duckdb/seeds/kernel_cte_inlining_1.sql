-- rule kernel: cte_inlining (duckdb)
SELECT a1.c2 AS c0, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c1, a1.c0 AS c2, '1999-12-31'::date AS c3 FROM t0 AS a1 WHERE NULLIF ((NOT COALESCE (FALSE, (EXISTS (SELECT a1.c0 AS c0)))), TRUE);
