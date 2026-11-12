-- rule kernel: ExistsToJoin (sqlite)
SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0, '2024-01-01 00:00:00' AS c1 FROM t0 AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0, a2.c0 AS c1, a1.c1 AS c2 FROM t1 AS a2));
