-- composition of rule kernels grouping_sets x limit_pushdown (duckdb), template product
SELECT count(*) FROM (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)) AS ka CROSS JOIN (SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)) AS ka) * (SELECT count(*) FROM (SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1) AS kb)
