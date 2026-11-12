-- composition of rule kernels L:type_coercion x P:OutputRequirements (datafusion), template exists
SELECT count(*) FROM (SELECT 2 AS c0) AS ka WHERE EXISTS (SELECT 1 FROM (SELECT 10::bigint AS c0, FALSE AS c1, make_array('a', 'b') AS c2, make_array(NULL, 1) AS c3) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT 10::bigint AS c0, FALSE AS c1, make_array('a', 'b') AS c2, make_array(NULL, 1) AS c3) AS kb) > 0 THEN (SELECT count(*) FROM (SELECT 2 AS c0) AS ka) ELSE 0 END
