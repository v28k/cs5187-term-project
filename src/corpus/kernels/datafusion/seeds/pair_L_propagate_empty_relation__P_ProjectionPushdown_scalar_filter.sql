-- composition of rule kernels L:propagate_empty_relation x P:ProjectionPushdown (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT 2 AS c0 FROM t3 AS a1 WHERE FALSE GROUP BY GROUPING SETS ((a1.c0), ()) UNION SELECT 10 AS c0) AS ka WHERE (SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 2 AS c0 FROM t3 AS a1 WHERE FALSE GROUP BY GROUPING SETS ((a1.c0), ()) UNION SELECT 10 AS c0) AS ka
