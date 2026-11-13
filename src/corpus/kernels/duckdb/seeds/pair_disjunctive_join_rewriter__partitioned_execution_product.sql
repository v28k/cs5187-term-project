-- composition of rule kernels disjunctive_join_rewriter x partitioned_execution (duckdb), template product
SELECT count(*) FROM (SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1) AS ka CROSS JOIN (FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1) AS ka) * (SELECT count(*) FROM (FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y) AS kb)
