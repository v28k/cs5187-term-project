-- rule kernel: L:extract_equijoin_predicate (datafusion)
SELECT '2000-01-01'::date AS c0 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) GROUP BY a1.c0, a2.c0 UNION ALL (SELECT '2024-02-29'::date AS c0 UNION SELECT '1999-12-31'::date AS c0);
