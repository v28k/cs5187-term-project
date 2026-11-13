-- rule kernel: window_self_join (duckdb)
SELECT AGE ((MAX ('2024-01-01 00:00:00+00'::timestamptz) OVER () - '0'::interval), '2024-02-29 12:34:56+00'::timestamptz) AS c0, 10 AS c1, 2 AS c2;
