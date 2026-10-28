-- pgfuzz failure 255e08379e82 (wrong_result, signature strength: diff)
-- test case 44782 from grammar
-- SQLSTATE -: result differs under plan variant no_memoize_material: 30 rows by default, 30 rows with variant
-- failing statement: #1
SELECT JSONB_AGG ((a3.c3 - a3.c3) ORDER BY (a3.c3 - a3.c3) DESC) AS c0 FROM (tp AS a1 JOIN (tp AS a2 FULL JOIN t4 AS a3 ON (a2.c0 = a3.c0)) ON (a1.c0 = a3.c0)) GROUP BY a1.c1, a3.c1;
VALUES (1000::bigint, (SELECT MAX ('6.333333333333333'::float8) FROM (t1 AS a1 CROSS JOIN ROWS FROM (GENERATE_SERIES (1, 5), UNNEST ('{}'::text[])) AS a2 (c0, c1))), 10), ((-1)::bigint, '50'::float8, ((7 % 100) * (WIDTH_BUCKET ('8.5714285714285714'::numeric, 0.0, 100.0, 10) % 100)));
