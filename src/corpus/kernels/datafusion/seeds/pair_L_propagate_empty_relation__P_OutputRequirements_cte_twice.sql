-- composition of rule kernels L:propagate_empty_relation x P:OutputRequirements (datafusion), template cte_twice
WITH ka AS (SELECT 18 AS c0, FALSE AS c1), kb AS (SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka) + (SELECT count(*) FROM (SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE) AS kb)
