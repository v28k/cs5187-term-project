-- composition of rule kernels grouping_sets x limit_pushdown (duckdb), template graft_exists
SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM (SELECT * FROM tp WHERE EXISTS (SELECT 1 FROM (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)) AS kb)) AS a1;
-- pgfuzz:check kernel:graft_exists SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1
