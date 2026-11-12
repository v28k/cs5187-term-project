-- composition of rule kernels DistinctOpt x PushDown (sqlite), template graft_scalar
SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN (SELECT * FROM t2 WHERE (SELECT count(*) FROM (SELECT CAST(' ' AS TEXT) AS c0, a1.n AS c1, CAST(42.5 AS NUMERIC) AS c2, a1.c0 AS c3 FROM v0 AS a1 WHERE ((UNICODE (CAST(' ' AS TEXT)) + 0) < a1.c0)) AS kb) >= 0) AS a3 ON ((a1.c3 = a3.c1) AND FALSE));
-- pgfuzz:check kernel:graft_scalar SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN t2 AS a3 ON ((a1.c3 = a3.c1) AND FALSE))
