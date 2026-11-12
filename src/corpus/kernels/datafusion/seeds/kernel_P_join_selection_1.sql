-- rule kernel: P:join_selection (datafusion)
SELECT '2000-01-01'::date AS c0 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) GROUP BY a2.c0, a2.c3 UNION ALL (SELECT '2024-01-01'::date AS c0 UNION SELECT '2024-01-01'::date AS c0);
