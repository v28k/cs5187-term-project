-- composition of rule kernels L:common_sub_expression_eliminate x L:eliminate_outer_join (datafusion), template graft_union
SELECT a2.c5 AS c0, a2.c2 AS c1 FROM ((SELECT * FROM ti UNION ALL SELECT * FROM ti WHERE (SELECT count(*) FROM (SELECT 16 AS c0, COALESCE (CASE WHEN TRUE THEN ARRAY[(SELECT MIN (0) FROM t2 AS a2)] ELSE ARRAY[1] END, make_array(NULL, 1)) AS c1 FROM ti AS a1) AS kb) < 0) AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1;
-- pgfuzz:check kernel:graft_union SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1
