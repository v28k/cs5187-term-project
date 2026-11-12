-- composition of rule kernels L:optimize_unions x L:type_coercion (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT 10::bigint AS c0, FALSE AS c1, make_array('a', 'b') AS c2, make_array(NULL, 1) AS c3) AS ka WHERE (SELECT count(*) FROM (SELECT '%'::text AS c0 INTERSECT (SELECT 'a'::text AS c0 UNION (SELECT '[1,10)'::text AS c0 UNION SELECT 'x%'::text AS c0))) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 10::bigint AS c0, FALSE AS c1, make_array('a', 'b') AS c2, make_array(NULL, 1) AS c3) AS ka
