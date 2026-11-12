-- rule kernel: OrderByIdxJoin (sqlite)
SELECT '2000-01-01 00:00:00' AS c0, FALSE AS c1 FROM (t1 AS a1 LEFT JOIN v0 AS a2 ON (a1.c0 = a2.c0)) GROUP BY a2.c0, a1.c0;
