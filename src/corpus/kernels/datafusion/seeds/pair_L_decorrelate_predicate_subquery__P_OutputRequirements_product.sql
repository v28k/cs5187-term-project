-- composition of rule kernels L:decorrelate_predicate_subquery x P:OutputRequirements (datafusion), template product
SELECT count(*) FROM (SELECT make_array(NULL, 1) AS c0, '-3 hours'::interval AS c1 FROM t2 AS a1 GROUP BY a1.c2 HAVING (ARRAY[1, 2, 3] IN (SELECT ARRAY[1] AS c0))) AS ka CROSS JOIN (SELECT 2 AS c0) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT make_array(NULL, 1) AS c0, '-3 hours'::interval AS c1 FROM t2 AS a1 GROUP BY a1.c2 HAVING (ARRAY[1, 2, 3] IN (SELECT ARRAY[1] AS c0))) AS ka) * (SELECT count(*) FROM (SELECT 2 AS c0) AS kb)
