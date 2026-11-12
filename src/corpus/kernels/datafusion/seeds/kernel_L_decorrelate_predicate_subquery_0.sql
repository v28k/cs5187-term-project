-- rule kernel: L:decorrelate_predicate_subquery (datafusion)
SELECT make_array(NULL, 1) AS c0, '-3 hours'::interval AS c1 FROM t2 AS a1 GROUP BY a1.c2 HAVING (ARRAY[1, 2, 3] IN (SELECT ARRAY[1] AS c0));
