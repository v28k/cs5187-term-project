-- rule kernel: L:push_down_filter (datafusion)
SELECT 6 AS c0, COALESCE (CASE WHEN TRUE THEN ARRAY[(SELECT MAX (a2.c0) FROM t0 AS a2 WHERE (29 >= a2.c0))] ELSE make_array(1, 2, 3) END, make_array(NULL, 1)) AS c1 FROM tl AS a1;
