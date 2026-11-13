-- rule kernel: DistinctOpt (sqlite)
SELECT DISTINCT a1.n AS c0 FROM (v0 AS a1 LEFT JOIN ti AS a2 ON (a1.c0 = a2.c0)) UNION ALL SELECT CAST(0 AS INTEGER) AS c0;
