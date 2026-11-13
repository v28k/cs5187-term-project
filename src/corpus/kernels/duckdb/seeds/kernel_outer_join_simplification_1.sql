-- rule kernel: outer_join_simplification (duckdb)
SELECT a2.c0 AS c0, '2024-01-01 00:00:00+00'::timestamptz AS c1 FROM (tp AS a1 JOIN (t0 AS a2 LEFT JOIN (t1 POSITIONAL JOIN tp) ON ((a2.c1 = tp.c1) AND TRUE)) ON ((a1.c0 = tp.c0) AND ('abc'::text NOT ILIKE '%\\%'::text))) QUALIFY (COUNT (*) OVER () = 1);
