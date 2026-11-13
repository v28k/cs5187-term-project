-- composition of rule kernels limit_pushdown x redundant_order (duckdb), template graft_scalar
SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM (SELECT * FROM tp WHERE (SELECT count(*) FROM (SELECT '0'::interval AS c0, '1999-12-31'::date AS c1, 0.0::float8 AS c2 FROM ti AS a1 WHERE (SELECT BOOL_OR (a2.c0) FROM (SELECT FALSE AS c0 ORDER BY ALL) AS a2)) AS kb) >= 0) AS a1;
-- pgfuzz:check kernel:graft_scalar SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1
