-- composition of rule kernels L:optimize_unions x L:propagate_empty_relation (datafusion), template graft_union
SELECT 2 AS c0 FROM (SELECT * FROM t3 UNION ALL SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT '2000-01-01'::date AS c0 UNION ALL (SELECT '2024-02-29'::date AS c0 UNION ALL (SELECT '1999-12-31'::date AS c0 UNION SELECT '2024-02-29'::date AS c0))) AS kb) < 0) AS a1 WHERE FALSE GROUP BY GROUPING SETS ((a1.c0), ()) UNION SELECT 10 AS c0;
-- pgfuzz:check kernel:graft_union SELECT 2 AS c0 FROM t3 AS a1 WHERE FALSE GROUP BY GROUPING SETS ((a1.c0), ()) UNION SELECT 10 AS c0
