-- composition of rule kernels L:extract_equijoin_predicate x P:ProjectionPushdown (datafusion), template not_exists
SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3))) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3))) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka) ELSE 0 END
