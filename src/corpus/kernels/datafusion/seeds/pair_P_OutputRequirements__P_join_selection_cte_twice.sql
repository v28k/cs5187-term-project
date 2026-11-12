-- composition of rule kernels P:OutputRequirements x P:join_selection (datafusion), template cte_twice
WITH ka AS (SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0))), kb AS (SELECT 18 AS c0, FALSE AS c1) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0))) AS ka) + (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS kb)
