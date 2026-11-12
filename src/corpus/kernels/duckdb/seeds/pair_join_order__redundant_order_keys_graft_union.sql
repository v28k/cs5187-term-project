-- composition of rule kernels join_order x redundant_order_keys (duckdb), template graft_union
SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM (SELECT * FROM t0 UNION ALL SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT (-1)::bigint AS c0, ({ 'a' : ((MAX ('2024-02-29'::date) OVER (PARTITION BY '{"k": 2, "a": [0]}'::jsonb) + 1) - '2024-01-01'::date), 'b' : '%'::text }).a AS c1 FROM (t4 POSITIONAL JOIN t1)) AS kb) < 0) AS a1 GROUP BY a1.c2;
-- pgfuzz:check kernel:graft_union SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2
