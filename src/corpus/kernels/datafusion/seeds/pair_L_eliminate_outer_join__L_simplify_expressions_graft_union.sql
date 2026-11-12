-- composition of rule kernels L:eliminate_outer_join x L:simplify_expressions (datafusion), template graft_union
SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN (SELECT * FROM t3 UNION ALL SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb) < 0) AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1;
-- pgfuzz:check kernel:graft_union SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1
