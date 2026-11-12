-- composition of rule kernels empty_result_pullup x unused_columns (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS ka WHERE (SELECT count(*) FROM (SELECT '2024-01-01'::date AS c0, (MAX ('epoch'::timestamptz) OVER () + '00:00:00.000001'::interval) AS c1 FROM tp AS a1 WHERE FALSE) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS ka
