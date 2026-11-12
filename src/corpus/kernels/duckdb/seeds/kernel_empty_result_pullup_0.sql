-- rule kernel: empty_result_pullup (duckdb)
SELECT '2024-01-01'::date AS c0, (MAX ('epoch'::timestamptz) OVER () + '00:00:00.000001'::interval) AS c1 FROM tp AS a1 WHERE FALSE;
