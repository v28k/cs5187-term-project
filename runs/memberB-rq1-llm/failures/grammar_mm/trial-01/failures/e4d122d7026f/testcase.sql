-- pgfuzz failure e4d122d7026f (wrong_result, signature strength: diff)
-- test case 57671 from grammar
-- SQLSTATE -: result differs under plan variant no_join_reorder: 8 rows by default, 8 rows with variant
-- failing statement: #1
SELECT JSONB_AGG ((a3.c3 - a3.c3) ORDER BY (a3.c3 - a3.c3) DESC) AS c0 FROM (tp AS a1 JOIN (t4 AS a2 FULL JOIN (t4 AS a3 LEFT JOIN v0 AS a4 ON (a3.c1 = a4.c0)) ON (a2.c0 = a4.c0)) ON (a1.c0 = a4.c0)) GROUP BY a1.c1, a3.c1;
VALUES (1000::bigint, (SELECT MAX ('6.333333333333333'::float8) FROM (t1 AS a1 CROSS JOIN ROWS FROM (GENERATE_SERIES (1, 5), UNNEST ('{}'::text[])) AS a2 (c0, c1))), 10), ((-1)::bigint, '50'::float8, ((7 % 100) * (WIDTH_BUCKET ('8.5714285714285714'::numeric, 0.0, 100.0, 10) % 100)));
