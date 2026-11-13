-- composition of rule kernels L:extract_equijoin_predicate x P:join_selection (datafusion), template graft_union
SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN (SELECT * FROM t4 UNION ALL SELECT * FROM t4 WHERE (SELECT count(*) FROM (SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0))) AS kb) < 0) AS a2 ON (a1.c3 = a2.c3));
-- pgfuzz:check kernel:graft_union SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3))
