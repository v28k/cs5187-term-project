-- pgfuzz failure 4878fcb5fe4b (assertion, signature strength: stack)
-- test case 42571 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #1
SELECT MIN ('34.50'::numeric) FILTER (WHERE FALSE) AS c0 FROM t2 AS a1, UNNEST (ARRAY['1'::text]) AS a2 (c0) GROUP BY CUBE (a1.c2, a1.c0) UNION SELECT COALESCE ('1.7142857142857143'::numeric, 0.5::numeric) AS c0 FROM JSON_TABLE (CASE WHEN ((ROW ((1.0 / 3)::float8, '_'::text) > ROW ('50'::float8, 'A'::text)) AND ('{"k": 0, "a": [3, 4, 5]}'::jsonb @@ 'exists($.a)')) THEN COALESCE (CASE WHEN TRUE THEN '{"k": 2, "a": [0]}'::jsonb ELSE '{"k": 0, "a": [3, 4, 5]}'::jsonb END, '{"k": 0, "a": [3, 4, 5]}'::jsonb) ELSE CASE WHEN (TRUE AND FALSE) THEN NULL::jsonb ELSE ('{"k": 0, "a": [3, 4, 5]}'::jsonb -> 0) END END, '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a3 ORDER BY 1;
