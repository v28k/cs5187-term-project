-- rule kernel: L:eliminate_filter (datafusion)
SELECT '0'::text AS c0, 10::bigint AS c1, 2 AS c2 FROM tl AS a1 GROUP BY a1.c1, a1.c0 HAVING TRUE;
