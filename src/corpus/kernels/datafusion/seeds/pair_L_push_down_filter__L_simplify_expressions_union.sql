-- composition of rule kernels L:push_down_filter x L:simplify_expressions (datafusion), template union
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS ka UNION ALL SELECT 2 AS k FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS ka) + (SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb)
