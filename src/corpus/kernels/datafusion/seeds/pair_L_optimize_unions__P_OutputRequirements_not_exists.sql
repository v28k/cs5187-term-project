-- composition of rule kernels L:optimize_unions x P:OutputRequirements (datafusion), template not_exists
SELECT count(*) FROM (SELECT 2 AS c0) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT '%'::text AS c0 INTERSECT (SELECT 'a'::text AS c0 UNION (SELECT '[1,10)'::text AS c0 UNION SELECT 'x%'::text AS c0))) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT '%'::text AS c0 INTERSECT (SELECT 'a'::text AS c0 UNION (SELECT '[1,10)'::text AS c0 UNION SELECT 'x%'::text AS c0))) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT 2 AS c0) AS ka) ELSE 0 END
