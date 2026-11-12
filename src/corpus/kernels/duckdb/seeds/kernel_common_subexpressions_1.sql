-- rule kernel: common_subexpressions (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT LIST_HAS_ALL (ARRAY[a1.c0], CASE WHEN TRUE THEN ARRAY_REVERSE (ARRAY[a1.c0]) ELSE ARRAY[1, 2, 3] END) AS c0, 'ß'::text AS c1 FROM t1 AS a1;
