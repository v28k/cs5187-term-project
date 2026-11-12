-- composition of rule kernels L:simplify_expressions x L:type_coercion (datafusion), template not_exists
SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT 10::bigint AS c0, FALSE AS c1, make_array('a', 'b') AS c2, make_array(NULL, 1) AS c3) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT 10::bigint AS c0, FALSE AS c1, make_array('a', 'b') AS c2, make_array(NULL, 1) AS c3) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS ka) ELSE 0 END
