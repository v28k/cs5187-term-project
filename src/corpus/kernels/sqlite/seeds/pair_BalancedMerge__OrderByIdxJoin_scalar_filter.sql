-- composition of rule kernels BalancedMerge x OrderByIdxJoin (sqlite), template scalar_filter
SELECT count(*) FROM (SELECT '2000-01-01 00:00:00' AS c0, FALSE AS c1 FROM (t1 AS a1 LEFT JOIN v0 AS a2 ON (a1.c0 = a2.c0)) GROUP BY a2.c0, a1.c0) AS ka WHERE (SELECT count(*) FROM (SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT '2000-01-01 00:00:00' AS c0, FALSE AS c1 FROM (t1 AS a1 LEFT JOIN v0 AS a2 ON (a1.c0 = a2.c0)) GROUP BY a2.c0, a1.c0) AS ka
