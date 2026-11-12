-- rule kernel: CoverIdxScan (sqlite)
SELECT '{"k": 1, "a": [1, 2]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, TRUE) <> (CASE WHEN FALSE THEN a1.c1 ELSE CONCAT_WS ('-', FALSE, (SELECT SUM (CAST(5e-324 AS REAL)) FROM t3 AS a2)) END, TRUE)) GROUP BY a1.c0, a1.c1;
