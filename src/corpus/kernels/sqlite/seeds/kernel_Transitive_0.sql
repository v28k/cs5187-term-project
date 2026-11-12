-- rule kernel: Transitive (sqlite)
SELECT a2.c2 AS c0, a3.c1 AS c1, a1.c1 AS c2, 10 AS c3 FROM (ti AS a1 INNER JOIN (t1 AS a2 JOIN t0 AS a3 ON ((a2.c0 = a3.c0) AND FALSE)) ON (a1.c0 = a3.c0));
