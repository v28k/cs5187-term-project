-- composition of rule kernels build_side_probe_side x grouping_sets (duckdb), template graft_union
SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM (SELECT * FROM tp UNION ALL SELECT * FROM tp WHERE (SELECT count(*) FROM (SELECT ((COUNT (DISTINCT a1.c5) % 1000)::int - 1) AS c0, a1.c5 AS c1, 'A'::text AS c2, COUNT (*) AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS kb) < 0) AS a1 GROUP BY CUBE (a1.c1);
-- pgfuzz:check kernel:graft_union SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)
