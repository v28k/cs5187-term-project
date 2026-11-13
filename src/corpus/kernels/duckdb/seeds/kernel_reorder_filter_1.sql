-- rule kernel: reorder_filter (duckdb)
SELECT (-1) AS c0 FROM (tl AS a1 JOIN (t1 POSITIONAL JOIN t3) ON ((a1.c0 = t3.c0) AND t3.c1)) WHERE GREATEST (((t1.c2 = '{"k": -1, "a": [1, 2, 3]}'::jsonb) OR TRUE), t3.c1);
