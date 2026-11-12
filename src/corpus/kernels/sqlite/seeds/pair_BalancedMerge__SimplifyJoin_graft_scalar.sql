-- composition of rule kernels BalancedMerge x SimplifyJoin (sqlite), template graft_scalar
SELECT a1.n AS c0 FROM ((SELECT * FROM v0 WHERE (SELECT count(*) FROM (SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1) AS kb) >= 0) AS a1 LEFT JOIN ti AS a2 ON ((a1.c0 = a2.c0) AND TRUE)) WHERE (a2.c1 <= CAST('%' AS TEXT)) UNION ALL SELECT CAST(1000 AS INTEGER) AS c0;
-- pgfuzz:check kernel:graft_scalar SELECT a1.n AS c0 FROM (v0 AS a1 LEFT JOIN ti AS a2 ON ((a1.c0 = a2.c0) AND TRUE)) WHERE (a2.c1 <= CAST('%' AS TEXT)) UNION ALL SELECT CAST(1000 AS INTEGER) AS c0
