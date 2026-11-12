-- composition of rule kernels grouping_sets x reorder_filter (duckdb), template graft_scalar
SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM (SELECT * FROM tp WHERE (SELECT count(*) FROM (SELECT 2.25::numeric AS c0, '0'::text AS c1, (SELECT COUNT (*) FROM t4 AS a1 WHERE ((a1.c3 <= 2.25::numeric) OR (a1.c0 IS NULL))) AS c2) AS kb) >= 0) AS a1 GROUP BY CUBE (a1.c1);
-- pgfuzz:check kernel:graft_scalar SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)
