-- rule kernel: common_subplan (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a4.c0 AS c0 FROM v0 AS a1, LATERAL (SELECT a3.c0 AS c0, a3.c1 AS c1 FROM v0 AS a2, (VALUES (1, 'a'::text), (2, NULL::text), (NULL::int, 'c'::text)) AS a3 (c0, c1)) AS a4;
