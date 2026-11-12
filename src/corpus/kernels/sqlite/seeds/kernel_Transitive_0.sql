-- rule kernel: Transitive (sqlite)
SELECT TRUE AS c0, '{"k": 2, "a": [0]}' AS c1, a1.c0 AS c2 FROM (((tp AS a1 INNER JOIN v0 AS a2 ON (a1.c0 = a2.c0)) JOIN t0 AS a3 ON (a1.c0 = a3.c0)) JOIN t0 AS a4 ON ((a1.c1 = a4.c1) AND FALSE));
