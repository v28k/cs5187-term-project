-- pgfuzz failure 65cd1cb9b0bf (performance, signature strength: message)
-- test case 8812 from grammar
-- SQLSTATE -: row estimate rises when the WHERE clause is added: 9.0 -> 18.0
-- failing statement: #7
CREATE TABLE n1 (c0 int, c1 int, c2 int[]) PARTITION BY RANGE (c0);
CREATE TABLE p2 PARTITION OF n1 FOR VALUES FROM (MINVALUE) TO (100);
CREATE TABLE p3 PARTITION OF n1 FOR VALUES FROM (100) TO (MAXVALUE);
CREATE TABLE p4 PARTITION OF n1 DEFAULT;
INSERT INTO n1 (c0, c1, c2) SELECT (100 - x), x, ARRAY[x % 3] FROM generate_series(1, 100) AS g(x);
ANALYZE n1;
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 20) SEARCH DEPTH FIRST BY c0 SET sq SELECT a1.c1 AS c0, (JSON_VALUE ('{}'::jsonb, '$.a[last]') IN (((CONCAT_WS ('-', TRUE, a2.c0) || a3.c1) || 'a'::text))) AS c1, LENGTH (SUBSTR (a3.c1, CARDINALITY (a4.c2))) AS c2, ('{"k": -1, "a": [1, 2, 3]}'::jsonb ->> (-1)) AS c3 FROM ((t1 AS a1 LEFT JOIN tp AS a2 ON (a1.c0 = a2.c0)) JOIN (tp AS a3 LEFT JOIN n1 AS a4 ON (a3.c0 = a4.c0)) ON ((a1.c0 = a4.c0) AND (TRUE AND (a4.c2 > '{1,2,3}'::int[])))) WHERE (a2.c1 NOT ILIKE 'A_C%'::text) ORDER BY 3;
