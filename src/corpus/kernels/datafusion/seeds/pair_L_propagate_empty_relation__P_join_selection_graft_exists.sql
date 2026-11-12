-- composition of rule kernels L:propagate_empty_relation x P:join_selection (datafusion), template graft_exists
SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN (SELECT * FROM t4 WHERE EXISTS (SELECT 1 FROM (SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE) AS kb)) AS a2 ON (a1.c0 = a2.c0));
-- pgfuzz:check kernel:graft_exists SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0))
