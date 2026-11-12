-- rule kernel: grouping_sets (duckdb)
SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1);
