-- rule kernel: disjunctive_join_rewriter (duckdb)
FROM (VALUES (1, 2)) a(x, y) JOIN (VALUES (1, 2)) b( y) ON a.x JOIN (VALUES (1, 2)) c(x, y) ON a.x = c.x OR a.y = c.y;
