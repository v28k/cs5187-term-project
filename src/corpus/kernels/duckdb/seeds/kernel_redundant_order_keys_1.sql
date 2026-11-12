-- rule kernel: redundant_order_keys (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT TRUE AS c0, TRUE AS c1, ARRAY['1'::text] AS c2 UNION SELECT FALSE AS c0, TRUE AS c1, ARRAY['1'::text] AS c2 ORDER BY 3, 3;
