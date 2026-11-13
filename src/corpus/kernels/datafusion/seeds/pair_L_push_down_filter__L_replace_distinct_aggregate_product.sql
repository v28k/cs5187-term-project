-- composition of rule kernels L:push_down_filter x L:replace_distinct_aggregate (datafusion), template product
SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS ka CROSS JOIN (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS ka) * (SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS kb)
