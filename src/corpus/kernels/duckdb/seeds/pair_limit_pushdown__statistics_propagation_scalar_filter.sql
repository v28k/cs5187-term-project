-- composition of rule kernels limit_pushdown x statistics_propagation (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT (SELECT MAX (a1.c0) FROM t4 AS a1 WHERE (EXISTS (SELECT 1::bigint AS c0))) AS c0, '2000-01-01'::date AS c1) AS ka WHERE (SELECT count(*) FROM (SELECT 20 AS c0, a1.c5 AS c1, 'A'::text AS c2, 1000::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT (SELECT MAX (a1.c0) FROM t4 AS a1 WHERE (EXISTS (SELECT 1::bigint AS c0))) AS c0, '2000-01-01'::date AS c1) AS ka
