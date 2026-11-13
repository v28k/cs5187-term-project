-- rule kernel: filter_pullup (duckdb)
SELECT 'x%'::text AS c0 EXCEPT ALL SELECT a1.c1 AS c0 FROM tl AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0 FROM v0 AS a2 WHERE NULL::boolean));
