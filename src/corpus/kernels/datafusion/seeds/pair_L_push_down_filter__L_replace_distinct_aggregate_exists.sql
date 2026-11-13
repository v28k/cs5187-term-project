-- composition of rule kernels L:push_down_filter x L:replace_distinct_aggregate (datafusion), template exists
SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS ka WHERE EXISTS (SELECT 1 FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb) > 0 THEN (SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS ka) ELSE 0 END
