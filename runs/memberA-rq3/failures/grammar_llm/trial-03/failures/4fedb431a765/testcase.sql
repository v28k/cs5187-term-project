-- pgfuzz failure 4fedb431a765 (internal_error, signature strength: message)
-- test case 8083 from grammar
-- SQLSTATE XX000: could not find pathkey item to sort
-- failing statement: #5
SET LOCAL parallel_setup_cost = 0;
SET LOCAL parallel_tuple_cost = 0;
SET LOCAL min_parallel_table_scan_size = 0;
SET LOCAL enable_hashjoin = OFF;
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION SELECT (r.c0 * 7) % 10 FROM rc AS r) CYCLE c0 SET cy USING pth SELECT '{}'::jsonb AS c0, a1.c1 AS c1 FROM t1 AS a1 WHERE FALSE UNION (SELECT '{"k": 2, "a": [0]}'::jsonb AS c0, a2.c0 AS c1 FROM tp AS a2 WHERE ('c4ca4238a0b923820dcc509a6f75849b'::text ^@ a2.c1) EXCEPT SELECT '{"k": 0, "a": [3, 4, 5]}'::jsonb AS c0, '39'::int AS c1 FROM t3 AS a3 WHERE TRUE);
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION SELECT (r.c0 * 7) % 10 FROM rc AS r) CYCLE c0 SET cy USING pth SELECT (JSONB_BUILD_OBJECT ('k', '2024-03-31'::date) @@ '$.k == 1') AS c0, a1.c0 AS c1, 10 AS c2 FROM ti AS a1 WHERE (NULL::int >= ANY (SELECT a1.c0 AS c0)) EXCEPT SELECT FALSE AS c0, a2.c0 AS c1, a2.c0 AS c2 FROM (SELECT 3 AS c0) AS a2 WHERE (TRUE IN (SELECT FALSE AS c0));
