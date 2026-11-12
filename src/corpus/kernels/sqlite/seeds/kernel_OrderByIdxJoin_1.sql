-- rule kernel: OrderByIdxJoin (sqlite)
SELECT '{"k": 2, "a": [0]}' AS c0, CAST('[1,10)' AS TEXT) AS c1 FROM (t1 AS a1 LEFT JOIN t1 AS a2 ON (a1.c0 = a2.c0)) GROUP BY a2.c1, a1.c0;
