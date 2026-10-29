-- pgfuzz failure 4fedb431a765 (internal_error, signature strength: message)
-- test case 15419 from grammar
-- SQLSTATE XX000: could not find pathkey item to sort
-- failing statement: #5
CREATE STATISTICS ON (COALESCE (c2, c2)) FROM t0;
ANALYZE t0;
CREATE STATISTICS ON (COALESCE (c3, c3)) FROM t1;
ANALYZE t1;
WITH cte1 AS NOT MATERIALIZED (SELECT a1.c2 AS c0 FROM t4 AS a1) SELECT (a3.c0)::numeric AS c0, 'a'::text AS c1 FROM (v0 AS a2 INNER JOIN t4 AS a3 ON ((a2.c0 = a3.c0) AND FALSE)) WHERE (a3.c2 LIKE '%b%'::text) UNION ALL (SELECT '34.50'::numeric AS c0, a4.c1 AS c1 FROM tl AS a4 WHERE TRUE EXCEPT SELECT '2.5'::numeric AS c0, a5.c1 AS c1 FROM tl AS a5);
