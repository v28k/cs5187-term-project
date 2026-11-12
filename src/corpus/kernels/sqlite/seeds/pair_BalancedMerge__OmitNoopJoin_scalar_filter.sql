-- composition of rule kernels BalancedMerge x OmitNoopJoin (sqlite), template scalar_filter
SELECT count(*) FROM (SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1) AS ka WHERE (SELECT count(*) FROM (SELECT DISTINCT a1.n AS c0 FROM (v0 AS a1 LEFT JOIN ti AS a2 ON (a1.c0 = a2.c0)) UNION ALL SELECT CAST(100 AS INTEGER) AS c0) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1) AS ka
