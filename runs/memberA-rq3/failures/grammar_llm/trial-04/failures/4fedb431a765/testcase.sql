-- pgfuzz failure 4fedb431a765 (internal_error, signature strength: message)
-- test case 2854 from grammar
-- SQLSTATE XX000: could not find pathkey item to sort
-- failing statement: #3
CLUSTER t0 USING i0;
SET LOCAL enable_presorted_aggregate = OFF;
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT (a3.c2 % 1000)::int AS c0, '0'::text AS c1 FROM (t1 AS a1 RIGHT JOIN t1 AS a2 ON (a1.c1 = a2.c1)), LATERAL (SELECT 3 AS c0, ARRAY_CAT ('{}'::int[], ARRAY[1, 2, 3]) AS c1, 10::bigint AS c2) AS a3, LATERAL (SELECT '7 days'::interval AS c0, '17.1428571428571429'::numeric AS c1) AS a4 WHERE (FALSE OR FALSE) UNION ALL (SELECT a5.c0 AS c0, 'ß'::text AS c1 FROM UNNEST (ARRAY[1]) WITH ORDINALITY AS a5 (c0, c1) WHERE TRUE INTERSECT ALL SELECT '180'::int AS c0, 'abc'::text AS c1 FROM t2 AS a6 GROUP BY CUBE (a6.c3, a6.c2));
