-- composition of rule kernels disjunctive_join_rewriter x partitioned_execution (duckdb), template scalar_filter
SELECT count(*) FROM (FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y) AS ka WHERE (SELECT count(*) FROM (SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y) AS ka
