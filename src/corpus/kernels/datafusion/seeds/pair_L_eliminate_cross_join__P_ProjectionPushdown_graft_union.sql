-- composition of rule kernels L:eliminate_cross_join x P:ProjectionPushdown (datafusion), template graft_union
SELECT 38 AS c0, ARRAY[1] AS c1 FROM (SELECT * FROM v0 UNION ALL SELECT * FROM v0 WHERE (SELECT count(*) FROM (SELECT 100 AS c0, 1.5::numeric AS c1, 5 AS c2, 0::bigint AS c3 FROM (ti AS a1 INNER JOIN (t4 AS a2 JOIN t4 AS a3 ON (a2.c0 = a3.c0)) ON ((a1.c0 = a3.c0) AND TRUE)) GROUP BY a1.c1) AS kb) < 0) AS a1;
-- pgfuzz:check kernel:graft_union SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1
