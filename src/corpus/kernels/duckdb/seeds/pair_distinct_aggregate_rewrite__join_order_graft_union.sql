-- composition of rule kernels distinct_aggregate_rewrite x join_order (duckdb), template graft_union
SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM (SELECT * FROM t0 UNION ALL SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT ((COUNT (DISTINCT a1.c5) % 1000)::int - 1) AS c0, a1.c5 AS c1, 'A'::text AS c2, 0::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS kb) < 0) AS a1 GROUP BY a1.c2;
-- pgfuzz:check kernel:graft_union SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2
