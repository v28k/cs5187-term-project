-- rule kernel: L:optimize_unions (datafusion)
SELECT '2000-01-01'::date AS c0 UNION ALL (SELECT '2024-02-29'::date AS c0 UNION ALL (SELECT '1999-12-31'::date AS c0 UNION SELECT '2024-02-29'::date AS c0));
