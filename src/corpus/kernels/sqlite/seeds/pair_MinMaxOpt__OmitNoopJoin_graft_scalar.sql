-- composition of rule kernels MinMaxOpt x OmitNoopJoin (sqlite), template graft_scalar
SELECT '{"k": 0, "a": [3, 4, 5]}' AS c0, (- (SELECT MIN (a2.c0) FROM (SELECT * FROM ti WHERE (SELECT count(*) FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 FROM (t3 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND a1.c1))) AS kb) >= 0) AS a2)) AS c1, CAST(10.0 AS NUMERIC) AS c2, 0 AS c3 FROM t0 AS a1;
-- pgfuzz:check kernel:graft_scalar SELECT '{"k": 0, "a": [3, 4, 5]}' AS c0, (- (SELECT MIN (a2.c0) FROM ti AS a2)) AS c1, CAST(10.0 AS NUMERIC) AS c2, 0 AS c3 FROM t0 AS a1
