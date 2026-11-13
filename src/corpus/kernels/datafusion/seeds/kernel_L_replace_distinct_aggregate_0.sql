-- rule kernel: L:replace_distinct_aggregate (datafusion)
SELECT 10 AS c0, 100 AS c1 UNION SELECT 2 AS c0, 0 AS c1;
