-- rule kernel: L:common_sub_expression_eliminate (datafusion)
SELECT 16 AS c0, COALESCE (CASE WHEN TRUE THEN ARRAY[(SELECT MIN (0) FROM t2 AS a2)] ELSE ARRAY[1] END, make_array(NULL, 1)) AS c1 FROM ti AS a1;
