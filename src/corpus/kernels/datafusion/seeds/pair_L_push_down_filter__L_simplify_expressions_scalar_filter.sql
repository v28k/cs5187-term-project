-- composition of rule kernels L:push_down_filter x L:simplify_expressions (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS ka WHERE (SELECT count(*) FROM (SELECT '_'::text AS c0, '2000-01-01'::date AS c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS ka
