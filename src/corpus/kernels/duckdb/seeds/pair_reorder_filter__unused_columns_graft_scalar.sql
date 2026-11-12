-- composition of rule kernels reorder_filter x unused_columns (duckdb), template graft_scalar
SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM (SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT 2.25::numeric AS c0, '0'::text AS c1, (SELECT COUNT (*) FROM t4 AS a1 WHERE ((a1.c3 <= 2.25::numeric) OR (a1.c0 IS NULL))) AS c2) AS kb) >= 0) AS a1 GROUP BY a1.c2;
-- pgfuzz:check kernel:graft_scalar SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2
