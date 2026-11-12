-- composition of rule kernels distinct_aggregate_rewrite x statistics_propagation (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT 20 AS c0, a1.c5 AS c1, 'A'::text AS c2, 1000::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS ka WHERE (SELECT count(*) FROM (SELECT ((COUNT (DISTINCT a1.c5) % 1000)::int - 1) AS c0, a1.c5 AS c1, 'A'::text AS c2, 0::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 20 AS c0, a1.c5 AS c1, 'A'::text AS c2, 1000::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS ka
