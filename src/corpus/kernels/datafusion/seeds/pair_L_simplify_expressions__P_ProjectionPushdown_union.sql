-- composition of rule kernels L:simplify_expressions x P:ProjectionPushdown (datafusion), template union
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka UNION ALL SELECT 2 AS k FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka) + (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb)
