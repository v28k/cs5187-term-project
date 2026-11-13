-- composition of rule kernels duplicate_groups x grouping_sets (duckdb), template graft_scalar
SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM (SELECT * FROM tp WHERE (SELECT count(*) FROM (SELECT ((COUNT (DISTINCT a1.c1) % 1000)::int - 1) AS c0, a1.c1 AS c1, 'A'::text AS c2, 1::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1) AS kb) >= 0) AS a1 GROUP BY CUBE (a1.c1);
-- pgfuzz:check kernel:graft_scalar SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)
