-- composition of rule kernels PushDown x SimplifyJoin (sqlite), template scalar_filter
SELECT count(*) FROM (SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))) AS ka WHERE (SELECT count(*) FROM (SELECT a1.c0 AS c0, CAST(0.5 AS REAL) AS c1, a2.c0 AS c2, '1970-01-01' AS c3 FROM (tp AS a1 FULL JOIN t4 AS a2 ON (a1.c0 = a2.c1)) WHERE (a2.c0 > 100)) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))) AS ka
