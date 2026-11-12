-- composition of rule kernels limit_pushdown x reorder_filter (duckdb), template graft_scalar
SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM (SELECT * FROM tp WHERE (SELECT count(*) FROM (SELECT (-1) AS c0 FROM (tl AS a1 JOIN (t1 POSITIONAL JOIN t3) ON ((a1.c0 = t3.c0) AND t3.c1)) WHERE GREATEST (((t1.c2 = '{"k": -1, "a": [1, 2, 3]}'::jsonb) OR TRUE), t3.c1)) AS kb) >= 0) AS a1;
-- pgfuzz:check kernel:graft_scalar SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1
