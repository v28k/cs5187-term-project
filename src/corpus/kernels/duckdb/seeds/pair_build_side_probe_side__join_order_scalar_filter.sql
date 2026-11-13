-- composition of rule kernels build_side_probe_side x join_order (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT ((COUNT (DISTINCT a1.c5) % 1000)::int - 1) AS c0, a1.c5 AS c1, 'A'::text AS c2, COUNT (*) AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS ka WHERE (SELECT count(*) FROM (SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT ((COUNT (DISTINCT a1.c5) % 1000)::int - 1) AS c0, a1.c5 AS c1, 'A'::text AS c2, COUNT (*) AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS ka
