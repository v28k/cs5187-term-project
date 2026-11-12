-- composition of rule kernels BalancedMerge x OmitNoopJoin (sqlite), template union
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 FROM (t3 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND a1.c1))) AS ka UNION ALL SELECT 2 AS k FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 FROM (t3 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND a1.c1))) AS ka) + (SELECT count(*) FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS kb)
