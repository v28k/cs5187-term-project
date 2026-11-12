-- rule kernel: Transitive (sqlite)
SELECT CAST(' ' AS TEXT) AS c0, CAST('%' AS TEXT) AS c1 FROM (t1 AS a1 JOIN (v0 AS a2 INNER JOIN ti AS a3 ON ((a2.c0 = a3.c0) AND TRUE)) ON ((a1.c0 = a3.c0) AND (a2.c0 = (-20)))) GROUP BY a1.c1, a1.c2, a1.c0;
