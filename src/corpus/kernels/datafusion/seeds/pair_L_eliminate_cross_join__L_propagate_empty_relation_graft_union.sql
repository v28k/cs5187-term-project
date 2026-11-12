-- composition of rule kernels L:eliminate_cross_join x L:propagate_empty_relation (datafusion), template graft_union
SELECT 'abc'::text AS c0 FROM (SELECT * FROM t1 UNION ALL SELECT * FROM t1 WHERE (SELECT count(*) FROM (SELECT 100 AS c0, 1.5::numeric AS c1, 5 AS c2, 0::bigint AS c3 FROM (ti AS a1 INNER JOIN (t4 AS a2 JOIN t4 AS a3 ON (a2.c0 = a3.c0)) ON ((a1.c0 = a3.c0) AND TRUE)) GROUP BY a1.c1) AS kb) < 0) AS a1 WHERE FALSE;
-- pgfuzz:check kernel:graft_union SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE
