-- composition of rule kernels L:simplify_expressions x P:ProjectionPushdown (datafusion), template graft_exists
SELECT 38 AS c0, ARRAY[1] AS c1 FROM (SELECT * FROM v0 WHERE EXISTS (SELECT 1 FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb)) AS a1;
-- pgfuzz:check kernel:graft_exists SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1
