-- composition of rule kernels compressed_materialization x empty_result_pullup (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1) AS ka WHERE (SELECT count(*) FROM (SELECT '2024-01-01'::date AS c0, (MAX ('epoch'::timestamptz) OVER () + '00:00:00.000001'::interval) AS c1 FROM tp AS a1 WHERE FALSE) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 41 AS c0, a1.c1 AS c1, 'A'::text AS c2, 100::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1) AS ka
