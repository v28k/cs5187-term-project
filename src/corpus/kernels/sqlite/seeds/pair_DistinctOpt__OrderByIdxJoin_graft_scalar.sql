-- composition of rule kernels DistinctOpt x OrderByIdxJoin (sqlite), template graft_scalar
SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN (SELECT * FROM t2 WHERE (SELECT count(*) FROM (SELECT '2000-01-01 00:00:00' AS c0, FALSE AS c1 FROM (t1 AS a1 LEFT JOIN v0 AS a2 ON (a1.c0 = a2.c0)) GROUP BY a2.c0, a1.c0) AS kb) >= 0) AS a3 ON ((a1.c3 = a3.c1) AND FALSE));
-- pgfuzz:check kernel:graft_scalar SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN t2 AS a3 ON ((a1.c3 = a3.c1) AND FALSE))
