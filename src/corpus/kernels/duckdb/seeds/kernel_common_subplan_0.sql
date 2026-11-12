-- rule kernel: common_subplan (duckdb)
SELECT 1.0::float8 AS c0, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c1, a1.c0 AS c2, '2000-01-01'::date AS c3 FROM tl AS a1 WHERE NULLIF ((NOT COALESCE (FALSE, (EXISTS (SELECT FALSE AS c0)))), TRUE);
