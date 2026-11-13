-- composition of rule kernels reorder_filter x statistics_propagation (duckdb), template graft_scalar
SELECT 20 AS c0, a1.c5 AS c1, 'A'::text AS c2, 1000::bigint AS c3 FROM (SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT 2.25::numeric AS c0, '0'::text AS c1, (SELECT COUNT (*) FROM t4 AS a1 WHERE ((a1.c3 <= 2.25::numeric) OR (a1.c0 IS NULL))) AS c2) AS kb) >= 0) AS a1 GROUP BY a1.c2, a1.c5;
-- pgfuzz:check kernel:graft_scalar SELECT 20 AS c0, a1.c5 AS c1, 'A'::text AS c2, 1000::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5
