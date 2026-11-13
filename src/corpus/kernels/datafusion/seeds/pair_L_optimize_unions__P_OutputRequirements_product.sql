-- composition of rule kernels L:optimize_unions x P:OutputRequirements (datafusion), template product
SELECT count(*) FROM (SELECT 2 AS c0) AS ka CROSS JOIN (SELECT '%'::text AS c0 INTERSECT (SELECT 'a'::text AS c0 UNION (SELECT '[1,10)'::text AS c0 UNION SELECT 'x%'::text AS c0))) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT 2 AS c0) AS ka) * (SELECT count(*) FROM (SELECT '%'::text AS c0 INTERSECT (SELECT 'a'::text AS c0 UNION (SELECT '[1,10)'::text AS c0 UNION SELECT 'x%'::text AS c0))) AS kb)
