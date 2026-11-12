-- composition of rule kernels BalancedMerge x PushDown (sqlite), template graft_scalar
SELECT CAST('A' AS TEXT) AS c0 FROM (SELECT * FROM v0 WHERE (SELECT count(*) FROM (SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1) AS kb) >= 0) AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)));
-- pgfuzz:check kernel:graft_scalar SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))
