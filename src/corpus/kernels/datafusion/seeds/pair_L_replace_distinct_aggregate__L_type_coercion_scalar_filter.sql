-- composition of rule kernels L:replace_distinct_aggregate x L:type_coercion (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS ka WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT make_array(NULL, 1) AS c0, 0.0::numeric AS c1 UNION SELECT ARRAY[1] AS c0, 0.5::numeric AS c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1) AS ka
