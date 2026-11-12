-- composition of rule kernels P:OutputRequirements x P:join_selection (datafusion), template union
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT 18 AS c0, FALSE AS c1) AS ka UNION ALL SELECT 2 AS k FROM (SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0))) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka) + (SELECT count(*) FROM (SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0))) AS kb)
