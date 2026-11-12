-- composition of rule kernels MinMaxOpt x OmitNoopJoin (sqlite), template graft_scalar
SELECT '{"k": 0, "a": [3, 4, 5]}' AS c0, (- (SELECT MIN (a2.c0) FROM ti AS a2)) AS c1, CAST(10.0 AS NUMERIC) AS c2, 0 AS c3 FROM (SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT DISTINCT a1.n AS c0 FROM (v0 AS a1 LEFT JOIN ti AS a2 ON (a1.c0 = a2.c0)) UNION ALL SELECT CAST(100 AS INTEGER) AS c0) AS kb) >= 0) AS a1;
-- pgfuzz:check kernel:graft_scalar SELECT '{"k": 0, "a": [3, 4, 5]}' AS c0, (- (SELECT MIN (a2.c0) FROM ti AS a2)) AS c1, CAST(10.0 AS NUMERIC) AS c2, 0 AS c3 FROM t0 AS a1
