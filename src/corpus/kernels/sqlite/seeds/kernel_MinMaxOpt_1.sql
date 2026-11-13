-- rule kernel: MinMaxOpt (sqlite)
SELECT '{"k": 0, "a": [3, 4, 5]}' AS c0, (- (SELECT MIN (a2.c0) FROM ti AS a2)) AS c1, CAST(10.0 AS NUMERIC) AS c2, 0 AS c3 FROM t0 AS a1;
