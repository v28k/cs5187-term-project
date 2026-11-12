-- rule kernel: common_aggregate (duckdb)
SELECT '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c0, 0.5::numeric AS c1, 1::bigint AS c2, 'a'::text AS c3 FROM t3 AS a1 HAVING BOOL_AND ((a1.c5 < ANY (SELECT 'NaN'::text AS c0)));
