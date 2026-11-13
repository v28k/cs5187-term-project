-- rule kernel: L:eliminate_filter (datafusion)
SELECT '2024-12-31'::date AS c0 UNION ALL (SELECT '2024-01-01'::date AS c0 FROM t4 AS a1 WHERE TRUE UNION ALL (SELECT '2024-02-29'::date AS c0 UNION SELECT '1999-12-31'::date AS c0));
