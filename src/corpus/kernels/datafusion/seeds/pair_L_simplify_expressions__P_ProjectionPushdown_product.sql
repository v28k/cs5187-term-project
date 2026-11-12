-- composition of rule kernels L:simplify_expressions x P:ProjectionPushdown (datafusion), template product
SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka CROSS JOIN (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka) * (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb)
