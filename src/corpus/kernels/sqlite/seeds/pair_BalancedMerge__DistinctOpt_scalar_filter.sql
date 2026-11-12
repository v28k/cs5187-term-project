-- composition of rule kernels BalancedMerge x DistinctOpt (sqlite), template scalar_filter
SELECT count(*) FROM (SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN t2 AS a3 ON ((a1.c3 = a3.c1) AND FALSE))) AS ka WHERE (SELECT count(*) FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN t2 AS a3 ON ((a1.c3 = a3.c1) AND FALSE))) AS ka
