-- composition of rule kernels grouping_sets x join_order (duckdb), template cte_twice
WITH ka AS (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)), kb AS (SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT ((- MIN (a1.c0)) + 500) AS c0 FROM tp AS a1 GROUP BY CUBE (a1.c1)) AS ka) + (SELECT count(*) FROM (SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS kb)
