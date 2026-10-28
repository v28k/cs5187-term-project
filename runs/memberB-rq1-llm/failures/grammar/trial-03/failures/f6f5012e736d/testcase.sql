-- pgfuzz failure f6f5012e736d (assertion, signature strength: stack)
-- test case 70894 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #4
CREATE TABLE n1 (c0 int PRIMARY KEY, c1 interval CHECK ((c1 IS NOT NULL) OR TRUE), c2 text);
INSERT INTO n1 (c0, c1, c2) SELECT x, (x * interval '1 minute'), md5(x::text) FROM generate_series(1, 20) AS g(x);
ANALYZE n1;
SELECT COALESCE (MAX (0.0::float8) OVER (PARTITION BY a1.c0, 0.5::numeric), ABS (COALESCE (10.0::float8, (58)::float8))) AS c0 FROM JSON_TABLE (JSONB_BUILD_OBJECT ('k', CASE WHEN (ROW (100.0::numeric, '0'::interval) >= ROW (NULL::numeric, '00:00:00.000001'::interval)) THEN COALESCE ('{}'::jsonb, '{"k": 0, "a": [3, 4, 5]}'::jsonb) ELSE JSON_QUERY ('{"k": 1, "a": [1, 2]}'::jsonb, '$.a[1]') END), '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a1;
INSERT INTO t1 AS a1 (c0, c1, c2, c3) VALUES (COALESCE (3, 0), NULLIF (NULL::int, 10), '{"k": 0, "a": [3, 4, 5]}'::jsonb, '[1,10)'::int4range) ON CONFLICT DO NOTHING RETURNING CASE WHEN FALSE THEN JSON_VALUE ((a1.c2 -> 'a'), '$.k') ELSE SUBSTR (REGEXP_REPLACE (ARRAY_TO_STRING ('{}'::text[], ','), '[a-c]+', 'X', 'g'), a1.c1) END AS c0, a1.c2 AS c1, a1.c0 AS c2;
