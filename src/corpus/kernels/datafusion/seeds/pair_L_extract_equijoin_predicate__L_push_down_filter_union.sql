-- composition of rule kernels L:extract_equijoin_predicate x L:push_down_filter (datafusion), template union
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3))) AS ka UNION ALL SELECT 2 AS k FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT 3 AS c0, ARRAY[1] AS c1 FROM (t4 AS a1 JOIN t4 AS a2 ON (a1.c3 = a2.c3))) AS ka) + (SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb)
