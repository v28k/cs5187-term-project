-- composition of rule kernels unused_columns x window_self_join (duckdb), template graft_scalar
SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM (SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT AGE ((MAX ('2024-01-01 00:00:00+00'::timestamptz) OVER () - '0'::interval), '2024-02-29 12:34:56+00'::timestamptz) AS c0, 10 AS c1, 2 AS c2) AS kb) >= 0) AS a1 GROUP BY a1.c2;
-- pgfuzz:check kernel:graft_scalar SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2
