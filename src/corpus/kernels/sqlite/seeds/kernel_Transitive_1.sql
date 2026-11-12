-- rule kernel: Transitive (sqlite)
SELECT CAST('NaN' AS TEXT) AS c0, a2.c3 AS c1 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3)) JOIN (SELECT CAST(1.0 AS REAL) AS c0, CAST(100.0 AS NUMERIC) AS c1 FROM t2 AS a3) AS a4 ON ((a1.c3 = a4.c1) AND FALSE)) GROUP BY a2.c3, a2.c0;
