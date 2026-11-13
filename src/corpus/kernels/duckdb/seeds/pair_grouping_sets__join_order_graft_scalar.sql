-- composition of rule kernels grouping_sets x join_order (duckdb), template graft_scalar
SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM (SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)) AS kb) >= 0) AS a1 GROUP BY a1.c2;
-- pgfuzz:check kernel:graft_scalar SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2
