-- rule kernel: redundant_order_keys (duckdb)
SELECT (-1)::bigint AS c0, ({ 'a' : ((MAX ('2024-02-29'::date) OVER (PARTITION BY '{"k": 2, "a": [0]}'::jsonb) + 1) - '2024-01-01'::date), 'b' : '%'::text }).a AS c1 FROM (t4 POSITIONAL JOIN t1);
