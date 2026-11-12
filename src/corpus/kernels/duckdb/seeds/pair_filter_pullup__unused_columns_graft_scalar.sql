-- composition of rule kernels filter_pullup x unused_columns (duckdb), template graft_scalar
SELECT 'x%'::text AS c0 EXCEPT ALL SELECT a1.c1 AS c0 FROM tl AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0 FROM (SELECT * FROM v0 WHERE (SELECT count(*) FROM (SELECT 0.5::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS kb) >= 0) AS a2 WHERE NULL::boolean));
-- pgfuzz:check kernel:graft_scalar SELECT 'x%'::text AS c0 EXCEPT ALL SELECT a1.c1 AS c0 FROM tl AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0 FROM v0 AS a2 WHERE NULL::boolean))
