-- composition of rule kernels P:EnsureRequirements x P:OutputRequirements (datafusion), template union
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS ka UNION ALL SELECT 2 AS k FROM (SELECT 2 AS c0) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS ka) + (SELECT count(*) FROM (SELECT 2 AS c0) AS kb)
