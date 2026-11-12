-- rule kernel: BloomFilter (sqlite)
SELECT '{"k": 2, "a": [0]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, CASE WHEN FALSE THEN TRUE ELSE (CAST(1 AS INTEGER) IN (SELECT CAST(100 AS INTEGER) AS c0)) END) <> (a1.c1, TRUE)) GROUP BY a1.c0, a1.c1;
