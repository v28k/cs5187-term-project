SELECT * FROM td LEFT JOIN ta ON ta.a = 3 LEFT JOIN tb ON ta.a = tb.b LEFT JOIN tc ON tc.c = tb.b;
SELECT * FROM td LEFT JOIN ta ON ta.a = 3 LEFT JOIN (tb LEFT JOIN tc ON tc.c = tb.b) ON ta.a = tb.b;
SELECT * FROM td LEFT JOIN (ta LEFT JOIN (tb LEFT JOIN tc ON tc.c = tb.b) ON ta.a = tb.b) ON ta.a = 3;
EXPLAIN (COSTS OFF) SELECT * FROM td LEFT JOIN ta ON ta.a = 3 LEFT JOIN (tb LEFT JOIN tc ON tc.c = tb.b) ON ta.a = tb.b;
