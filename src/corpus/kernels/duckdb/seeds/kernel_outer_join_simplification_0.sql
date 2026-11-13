-- rule kernel: outer_join_simplification (duckdb)
SELECT 0 AS c0 FROM (tl AS a1 JOIN (t1 AS a2 FULL JOIN v0 AS a3 ON (a2.c1 = a3.c0)) ON ((a1.c0 = a3.c0) AND TRUE));
