-- rule kernel: L:type_coercion (datafusion)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT make_array(NULL, 1) AS c0, 0.0::numeric AS c1 UNION SELECT ARRAY[1] AS c0, 0.5::numeric AS c1;
