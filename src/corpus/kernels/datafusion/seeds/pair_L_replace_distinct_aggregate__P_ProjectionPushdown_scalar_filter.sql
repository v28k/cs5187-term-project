-- composition of rule kernels L:replace_distinct_aggregate x P:ProjectionPushdown (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS ka WHERE (SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS ka
