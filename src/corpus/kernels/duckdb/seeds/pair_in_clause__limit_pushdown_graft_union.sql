-- composition of rule kernels in_clause x limit_pushdown (duckdb), template graft_union
SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM (SELECT * FROM tp UNION ALL SELECT * FROM tp WHERE (SELECT count(*) FROM (SELECT a1.c0 AS c0, a1.c1 AS c1, a1.c2 AS c2, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c3 FROM t0 AS a1 GROUP BY a1.c1, a1.c2, a1.c0 HAVING (a1.c2 IN (MAX (a1.c2)))) AS kb) < 0) AS a1;
-- pgfuzz:check kernel:graft_union SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1
