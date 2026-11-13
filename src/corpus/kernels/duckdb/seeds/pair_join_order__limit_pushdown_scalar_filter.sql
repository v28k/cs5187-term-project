-- composition of rule kernels join_order x limit_pushdown (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT (SELECT MAX (a1.c0) FROM t4 AS a1 WHERE (EXISTS (SELECT 1::bigint AS c0))) AS c0, '2000-01-01'::date AS c1) AS ka WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT 0 AS c0 UNION SELECT 7 AS c0) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT (SELECT MAX (a1.c0) FROM t4 AS a1 WHERE (EXISTS (SELECT 1::bigint AS c0))) AS c0, '2000-01-01'::date AS c1) AS ka
