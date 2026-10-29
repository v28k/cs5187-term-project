-- pgfuzz failure ec8b42ef87ac (assertion, signature strength: stack)
-- test case 25517 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #6
ANALYZE ti;
CREATE TABLE n1 (c0 int, c1 int GENERATED ALWAYS AS (c0) VIRTUAL) PARTITION BY LIST (c0);
CREATE TABLE p2 PARTITION OF n1 FOR VALUES IN (1, 2, 3);
CREATE TABLE p3 PARTITION OF n1 DEFAULT;
INSERT INTO n1 (c0) SELECT (100 - x) FROM generate_series(1, 100) AS g(x);
SELECT LENGTH (MIN (LEAST (a1.c1, CONCAT_WS ('-', '{"k": 1, "a": [1, 2]}'::jsonb, a3.c1)))) AS c0, COALESCE (COALESCE ('[1,10)'::int4range, '(,)'::int4range), '(,5]'::int4range) AS c1 FROM tl AS a1, LATERAL (SELECT a1.c1 AS c0, FALSE AS c1 FROM JSON_TABLE (CASE WHEN ((ROW ((1.0 / 3)::float8, '_'::text) > ROW ('50'::float8, 'A'::text)) AND ('{"k": 0, "a": [3, 4, 5]}'::jsonb @@ 'exists($.a)')) THEN COALESCE (CASE WHEN TRUE THEN '{"k": 2, "a": [0]}'::jsonb ELSE '{"k": 0, "a": [3, 4, 5]}'::jsonb END, '{"k": 0, "a": [3, 4, 5]}'::jsonb) ELSE CASE WHEN (TRUE AND FALSE) THEN NULL::jsonb ELSE ('{"k": 0, "a": [3, 4, 5]}'::jsonb -> 0) END END, '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a2 GROUP BY a2.c0) AS a3 GROUP BY a3.c0 ORDER BY 1;
