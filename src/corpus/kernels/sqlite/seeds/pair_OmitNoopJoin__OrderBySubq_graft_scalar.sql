-- composition of rule kernels OmitNoopJoin x OrderBySubq (sqlite), template graft_scalar
SELECT CAST(42.5 AS NUMERIC) AS c0 FROM (t3 AS a1 LEFT JOIN (SELECT * FROM t1 WHERE (SELECT count(*) FROM (SELECT TRUE AS c0, TRUE AS c1 FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 UNION SELECT CAST(1.5 AS NUMERIC) AS c0) AS a1 GROUP BY a1.c0) AS kb) >= 0) AS a2 ON ((a1.c0 = a2.c0) AND a1.c1));
-- pgfuzz:check kernel:graft_scalar SELECT CAST(42.5 AS NUMERIC) AS c0 FROM (t3 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND a1.c1))
