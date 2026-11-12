-- composition of rule kernels filter_pullup x grouping_sets (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)) AS ka WHERE (SELECT count(*) FROM (SELECT 'x%'::text AS c0 EXCEPT ALL SELECT a1.c1 AS c0 FROM tl AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0 FROM v0 AS a2 WHERE NULL::boolean))) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)) AS ka
