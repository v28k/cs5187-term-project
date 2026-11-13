-- composition of rule kernels aggregate_function_rewriter x limit_pushdown (duckdb), template graft_union
SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM (SELECT * FROM tp UNION ALL SELECT * FROM tp WHERE (SELECT count(*) FROM (SELECT (NULLIF (((LIST_SUM (LIST (35 ORDER BY 35)))::int % NULLIF (500, 0)), (-42)) + (-10)) AS c0 FROM t2 AS a1 GROUP BY GROUPING SETS ((a1.c1), (a1.c2), ())) AS kb) < 0) AS a1;
-- pgfuzz:check kernel:graft_union SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1
