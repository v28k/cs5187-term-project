-- pgfuzz failure 4fedb431a765 (internal_error, signature strength: message)
-- test case 27592 from grammar
-- SQLSTATE XX000: could not find pathkey item to sort
-- failing statement: #1
EXPLAIN (COSTS OFF) SELECT '2024-02-29'::date AS c0, CASE WHEN FALSE THEN a1.n ELSE 1::bigint END AS c1 FROM v0 AS a1 WHERE FALSE UNION (SELECT '2000-01-01'::date AS c0, a2.n AS c1 FROM v0 AS a2 WHERE (a2.c0 < (-1)) GROUP BY a2.n, a2.c0 EXCEPT ALL SELECT NULL::date AS c0, 100::bigint AS c1 FROM t3 AS a3 WHERE TRUE);
