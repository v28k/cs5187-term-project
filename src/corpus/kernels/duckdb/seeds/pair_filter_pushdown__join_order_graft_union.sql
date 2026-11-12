-- composition of rule kernels filter_pushdown x join_order (duckdb), template graft_union
SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM (SELECT * FROM t0 UNION ALL SELECT * FROM t0 WHERE (SELECT count(*) FROM (SELECT '2024-01-01'::date AS c0, (MAX ('1999-12-31 23:59:59.999999+05:30'::timestamptz) OVER (PARTITION BY '2000-01-01 00:00:00+00'::timestamptz) + '00:00:00.000001'::interval) AS c1 FROM t1 AS a1 WHERE NULLIF ((NULL::int < 2), FALSE)) AS kb) < 0) AS a1 GROUP BY a1.c2;
-- pgfuzz:check kernel:graft_union SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2
