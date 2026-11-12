-- composition of rule kernels in_clause x join_order (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS ka WHERE (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1 UNION (SELECT TRUE AS c0, 0.0::numeric AS c1 UNION BY NAME SELECT LIST_CONTAINS ([NULL, 1]::int[], a1.c0) AS c0, 2.25::numeric AS c1 FROM t3 AS a1)) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 0.0::numeric AS c0, 'a'::text AS c1 FROM t0 AS a1 GROUP BY a1.c2) AS ka
