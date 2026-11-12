-- rule kernel: PushDown (sqlite)
SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)));
