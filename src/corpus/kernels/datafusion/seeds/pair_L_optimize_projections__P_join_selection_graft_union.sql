-- composition of rule kernels L:optimize_projections x P:join_selection (datafusion), template graft_union
SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM (SELECT * FROM t3 UNION ALL SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT '2000-01-01'::date AS c0 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) GROUP BY a2.c0, a2.c3 UNION ALL (SELECT '2024-01-01'::date AS c0 UNION SELECT '2024-01-01'::date AS c0)) AS kb) < 0) AS a1;
-- pgfuzz:check kernel:graft_union SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1
