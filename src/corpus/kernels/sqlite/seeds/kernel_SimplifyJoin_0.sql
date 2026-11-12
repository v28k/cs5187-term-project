-- rule kernel: SimplifyJoin (sqlite)
SELECT a1.n AS c0 FROM (v0 AS a1 LEFT JOIN ti AS a2 ON ((a1.c0 = a2.c0) AND TRUE)) WHERE (a2.c1 <= CAST('%' AS TEXT)) UNION ALL SELECT CAST(1000 AS INTEGER) AS c0;
