-- composition of rule kernels L:eliminate_filter x L:propagate_empty_relation (datafusion), template graft_scalar
SELECT 2 AS c0 FROM (SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT '2024-12-31'::date AS c0 UNION ALL (SELECT '2024-01-01'::date AS c0 FROM t4 AS a1 WHERE TRUE UNION ALL (SELECT '2024-02-29'::date AS c0 UNION SELECT '1999-12-31'::date AS c0))) AS kb) >= 0) AS a1 WHERE FALSE GROUP BY GROUPING SETS ((a1.c0), ()) UNION SELECT 10 AS c0;
-- pgfuzz:check kernel:graft_scalar SELECT 2 AS c0 FROM t3 AS a1 WHERE FALSE GROUP BY GROUPING SETS ((a1.c0), ()) UNION SELECT 10 AS c0
