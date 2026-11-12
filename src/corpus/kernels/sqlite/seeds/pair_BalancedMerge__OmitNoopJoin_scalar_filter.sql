-- composition of rule kernels BalancedMerge x OmitNoopJoin (sqlite), template scalar_filter
SELECT count(*) FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS ka WHERE (SELECT count(*) FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 FROM (t3 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND a1.c1))) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS ka
