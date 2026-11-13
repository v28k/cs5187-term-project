-- composition of rule kernels disjunctive_join_rewriter x statistics_propagation (duckdb), template scalar_filter
SELECT count(*) FROM (FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y) AS ka WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT 100 AS c0, 16 AS c1 UNION SELECT 27 AS c0, 17 AS c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y) AS ka
