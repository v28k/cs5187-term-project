-- composition of rule kernels L:propagate_empty_relation x L:push_down_filter (datafusion), template product
SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS ka CROSS JOIN (SELECT 2 AS c0 FROM t3 AS a1 WHERE FALSE GROUP BY GROUPING SETS ((a1.c0), ()) UNION SELECT 10 AS c0) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS ka) * (SELECT count(*) FROM (SELECT 2 AS c0 FROM t3 AS a1 WHERE FALSE GROUP BY GROUPING SETS ((a1.c0), ()) UNION SELECT 10 AS c0) AS kb)
