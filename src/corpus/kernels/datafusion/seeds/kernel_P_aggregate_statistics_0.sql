-- rule kernel: P:aggregate_statistics (datafusion)
SELECT '0'::text AS c0, 3 AS c1, GREATEST (1000::bigint, COALESCE (NULLIF (1000::bigint, (SELECT COUNT (*) FROM tl AS a2)), 1000::bigint)) AS c2, a1.c1 AS c3 FROM tp AS a1;
