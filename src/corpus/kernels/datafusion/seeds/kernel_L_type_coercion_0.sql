-- rule kernel: L:type_coercion (datafusion)
SELECT 10::bigint AS c0, FALSE AS c1, make_array('a', 'b') AS c2, make_array(NULL, 1) AS c3;
