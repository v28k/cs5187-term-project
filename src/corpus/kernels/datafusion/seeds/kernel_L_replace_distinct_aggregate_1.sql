-- rule kernel: L:replace_distinct_aggregate (datafusion)
SELECT '2000-01-01'::date AS c0, 'NaN'::text AS c1 UNION SELECT '1999-12-31'::date AS c0, 'abc'::text AS c1;
