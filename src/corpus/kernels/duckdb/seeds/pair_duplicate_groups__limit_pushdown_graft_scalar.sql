-- composition of rule kernels duplicate_groups x limit_pushdown (duckdb), template graft_scalar
SELECT (SELECT MAX (a1.c0) FROM (SELECT * FROM t4 WHERE (SELECT count(*) FROM (SELECT 10::bigint AS c0 EXCEPT SELECT 10::bigint AS c0 FROM t4 AS a1 GROUP BY a1.c1, a1.c0, a1.c3) AS kb) >= 0) AS a1 WHERE (EXISTS (SELECT 1::bigint AS c0))) AS c0, '2000-01-01'::date AS c1;
-- pgfuzz:check kernel:graft_scalar SELECT (SELECT MAX (a1.c0) FROM t4 AS a1 WHERE (EXISTS (SELECT 1::bigint AS c0))) AS c0, '2000-01-01'::date AS c1
