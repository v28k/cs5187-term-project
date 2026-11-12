-- composition of rule kernels L:eliminate_outer_join x P:join_selection (datafusion), template graft_scalar
SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN (SELECT * FROM t4 WHERE (SELECT count(*) FROM (SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1) AS kb) >= 0) AS a2 ON (a1.c0 = a2.c0));
-- pgfuzz:check kernel:graft_scalar SELECT 6 AS c0, make_array(NULL, 1) AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0))
