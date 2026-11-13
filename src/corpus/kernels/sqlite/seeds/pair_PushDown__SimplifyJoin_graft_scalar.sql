-- composition of rule kernels PushDown x SimplifyJoin (sqlite), template graft_scalar
SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM (SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT a1.n AS c0 FROM (v0 AS a1 LEFT JOIN ti AS a2 ON ((a1.c0 = a2.c0) AND TRUE)) WHERE (a2.c1 <= CAST('%' AS TEXT)) UNION ALL SELECT CAST(1000 AS INTEGER) AS c0) AS kb) >= 0) AS a2) - 54) > (-8)));
-- pgfuzz:check kernel:graft_scalar SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))
