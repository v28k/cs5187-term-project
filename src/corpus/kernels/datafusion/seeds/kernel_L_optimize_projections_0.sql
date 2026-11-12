-- rule kernel: L:optimize_projections (datafusion)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0, 100.0::float8 AS c1 FROM t0 AS a1, generate_series (10, 1) AS a2 (c0) GROUP BY GROUPING SETS ((a1.c1), ());
