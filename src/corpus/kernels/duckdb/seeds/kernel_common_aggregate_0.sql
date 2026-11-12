-- rule kernel: common_aggregate (duckdb)
SELECT a1.c0 AS c0, a1.c0 AS c1 FROM t3 AS a1 WHERE (2 > ALL (SELECT a1.c0 AS c0)) INTERSECT (SELECT 17 AS c0, 10 AS c1 UNION SELECT 22 AS c0, 1 AS c1);
