-- composition of rule kernels L:optimize_projections x L:replace_distinct_aggregate (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS ka WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0, 100.0::float8 AS c1 FROM t0 AS a1, generate_series (10, 1) AS a2 (c0) GROUP BY GROUPING SETS ((a1.c1), ())) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS ka
