-- composition of rule kernels distinct_aggregate_rewrite x partitioned_execution (duckdb), template graft_union
SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM (SELECT * FROM tl UNION ALL SELECT * FROM tl WHERE (SELECT count(*) FROM (SELECT '2000-01-01 00:00:00+00'::timestamptz AS c0, 1.5::numeric AS c1, (- CASE WHEN FALSE THEN (SELECT SUM (DISTINCT a2.c1) FROM t2 AS a2) ELSE 2.25::numeric END) AS c2, 10 AS c3 FROM t1 AS a1) AS kb) < 0) AS a1;
-- pgfuzz:check kernel:graft_union SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1
