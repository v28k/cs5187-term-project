-- rule kernel: OrderByIdxJoin (sqlite)
WITH cte1 AS (SELECT 22 AS c0) SELECT a2.c1 AS c0, CAST('ß' AS TEXT) AS c1 FROM (t1 AS a1 JOIN t1 AS a2 ON (a1.c1 = a2.c1)) WHERE (a1.c0 = 3) ORDER BY 1;
