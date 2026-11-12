-- composition of rule kernels compressed_materialization x in_clause (duckdb), template graft_scalar
SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM (SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT a1.c0 AS c0, a1.c1 AS c1, a1.c2 AS c2, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c3 FROM t0 AS a1 GROUP BY a1.c1, a1.c2, a1.c0 HAVING (a1.c2 IN (MAX (a1.c2)))) AS kb) >= 0) AS a1 GROUP BY a1.c1;
-- pgfuzz:check kernel:graft_scalar SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1
