-- composition of rule kernels L:eliminate_outer_join x P:EnsureRequirements (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1) AS ka WHERE (SELECT count(*) FROM (SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1) AS ka
