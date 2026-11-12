-- rule kernel: L:extract_equijoin_predicate (datafusion)
SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3));
