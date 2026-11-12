-- composition of rule kernels deliminator x limit_pushdown (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1) AS ka WHERE (SELECT count(*) FROM (SELECT 'A'::text AS c0 FROM t0 AS a1, LATERAL (SELECT '1999-12-31 23:59:59.999999+05:30'::timestamptz AS c0, a1.c1 AS c1) AS a2 EXCEPT ALL SELECT 'A'::text AS c0) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT COALESCE ((EXISTS (SELECT 10.0::numeric AS c0, 1::bigint AS c1)), TRUE) AS c0 FROM tp AS a1) AS ka
