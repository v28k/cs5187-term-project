EXPLAIN (COSTS OFF)
SELECT *
FROM (SELECT 1 AS id) v
LEFT JOIN (
  SELECT 42 AS const_val, t3.c0 AS col_val
  FROM t3
  WHERE NOT EXISTS (SELECT 1 FROM t1 WHERE t1.c0 = t3.c0)
) sub ON true
WHERE sub.col_val = sub.const_val;
