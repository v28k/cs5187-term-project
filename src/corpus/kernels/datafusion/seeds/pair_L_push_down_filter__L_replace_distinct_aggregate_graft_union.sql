-- composition of rule kernels L:push_down_filter x L:replace_distinct_aggregate (datafusion), template graft_union
SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM (SELECT * FROM t3 UNION ALL SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS kb) < 0) AS a1 WHERE a1.c1;
-- pgfuzz:check kernel:graft_union SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1
