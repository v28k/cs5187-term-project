-- composition of rule kernels L:extract_equijoin_predicate x P:ProjectionPushdown (datafusion), template graft_exists
SELECT 38 AS c0, ARRAY[1] AS c1 FROM (SELECT * FROM v0 WHERE EXISTS (SELECT 1 FROM (SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3))) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3))) AS kb)) AS a1;
-- pgfuzz:check kernel:graft_exists SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1
