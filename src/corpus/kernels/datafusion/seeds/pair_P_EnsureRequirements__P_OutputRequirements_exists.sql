-- composition of rule kernels P:EnsureRequirements x P:OutputRequirements (datafusion), template exists
SELECT count(*) FROM (SELECT 2 AS c0) AS ka WHERE EXISTS (SELECT 1 FROM (SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1) AS kb) > 0 THEN (SELECT count(*) FROM (SELECT 2 AS c0) AS ka) ELSE 0 END
