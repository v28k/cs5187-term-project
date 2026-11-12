-- composition of rule kernels in_clause x unused_columns (duckdb), template graft_scalar
SELECT a1.c0 AS c0, a1.c1 AS c1, a1.c2 AS c2, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c3 FROM (SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS kb) >= 0) AS a1 GROUP BY a1.c1, a1.c2, a1.c0 HAVING (a1.c2 IN (MAX (a1.c2)));
-- pgfuzz:check kernel:graft_scalar SELECT a1.c0 AS c0, a1.c1 AS c1, a1.c2 AS c2, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c3 FROM t0 AS a1 GROUP BY a1.c1, a1.c2, a1.c0 HAVING (a1.c2 IN (MAX (a1.c2)))
