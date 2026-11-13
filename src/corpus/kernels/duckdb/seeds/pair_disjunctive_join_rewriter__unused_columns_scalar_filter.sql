-- composition of rule kernels disjunctive_join_rewriter x unused_columns (duckdb), template scalar_filter
SELECT count(*) FROM (FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) b( y) ON a.x JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y) AS ka WHERE (SELECT count(*) FROM (SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) b( y) ON a.x JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y) AS ka
