SELECT a1.c0, count(j_alias) FROM t1 AS a1 LEFT JOIN (t2 AS a2 JOIN t3 AS a3 ON a2.c0 = a3.c0) AS j_alias ON TRUE GROUP BY a1.c0;
