-- composition of rule kernels L:eliminate_outer_join x P:OutputRequirements (datafusion), template not_exists
SELECT count(*) FROM (SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT 18 AS c0, FALSE AS c1) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT 18 AS c0, FALSE AS c1) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT a2.c5 AS c0, a2.c2 AS c1 FROM (ti AS a1 LEFT JOIN t3 AS a2 ON (a1.c1 = a2.c5)) WHERE a2.c1) AS ka) ELSE 0 END
