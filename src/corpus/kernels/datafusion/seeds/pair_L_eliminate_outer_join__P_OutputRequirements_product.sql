-- composition of rule kernels L:eliminate_outer_join x P:OutputRequirements (datafusion), template product
SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka CROSS JOIN (SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS ka) * (SELECT count(*) FROM (SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1) AS kb)
