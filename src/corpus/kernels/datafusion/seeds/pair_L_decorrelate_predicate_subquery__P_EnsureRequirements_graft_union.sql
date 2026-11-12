-- composition of rule kernels L:decorrelate_predicate_subquery x P:EnsureRequirements (datafusion), template graft_union
SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM (SELECT * FROM t3 UNION ALL SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT make_array(NULL, 1) AS c0, '-3 hours'::interval AS c1 FROM t2 AS a1 GROUP BY a1.c2 HAVING (ARRAY[1, 2, 3] IN (SELECT ARRAY[1] AS c0))) AS kb) < 0) AS a1 WHERE a1.c1;
-- pgfuzz:check kernel:graft_union SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1
