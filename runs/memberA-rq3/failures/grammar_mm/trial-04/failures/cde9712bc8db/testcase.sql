-- pgfuzz failure cde9712bc8db (assertion, signature strength: stack)
-- test case 11412 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #2
SELECT '[0,0]'::int4range AS c0, 'ß'::text AS c1 FROM v0 AS a1 WHERE ISEMPTY (int4range(2, 40)) INTERSECT ALL SELECT '[1,10)'::int4range AS c0, MD5 ('0'::text) AS c1 FROM (SELECT '1'::int AS c0) AS a2 WHERE ('{}'::jsonb @@ '$.a[*] > 1');
SELECT '10'::int AS c0, INITCAP (a1.c2) AS c1 FROM t4 AS a1, JSON_TABLE ((JSONB_BUILD_OBJECT ('k', 1, 'a', JSONB_BUILD_ARRAY (JSON_VALUE ('{"k": -1, "a": [1, 2, 3]}'::jsonb, '$.k ? (@ > 0)'), (ROW ('2000-01-01'::date, 'é'::text) < ROW ('1999-12-31'::date, '0'::text)))) - 'k'), '$.a[*]' COLUMNS (c0 FOR ORDINALITY, c1 int PATH '$')) AS a2 EXCEPT ALL SELECT 10 AS c0, '{"k": 1}'::text AS c1 ORDER BY 1 NULLS FIRST;
