-- pgfuzz failure cc7181e74014 (assertion, signature strength: stack)
-- test case 47775 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #9
SET LOCAL enable_partitionwise_join = ON;
CREATE TABLE n1 (c0 int, c1 int, c2 numeric) PARTITION BY RANGE (c0);
CREATE TABLE p2 PARTITION OF n1 FOR VALUES FROM (MINVALUE) TO (100);
CREATE TABLE p3 PARTITION OF n1 FOR VALUES FROM (100) TO (MAXVALUE);
CREATE TABLE p4 PARTITION OF n1 DEFAULT;
INSERT INTO n1 (c0, c1, c2) SELECT (x % 3), (x % 3), round((x / 7.0)::numeric, 2) FROM generate_series(1, 20) AS g(x);
ANALYZE n1;
WITH cte1 AS NOT MATERIALIZED (SELECT GREATEST (CASE WHEN FALSE THEN '16'::int ELSE '200'::int END, (-1)) AS c0, '{"k": 0, "a": [3, 4, 5]}'::jsonb AS c1 FROM (tl AS a1 LEFT OUTER JOIN t0 AS a2 ON (a1.c0 = a2.c0)) GROUP BY GROUPING SETS ((a2.c1), (a1.c1), (a2.c2), ())) SELECT 0.5::numeric AS c0, '67.66666666666667'::float8 AS c1 FROM ((tp AS a3 LEFT JOIN tl AS a4 ON ((a3.c1 = a4.c1) AND (a4.c1 > 'c4ca4238a0b923820dcc509a6f75849b'::text))) LEFT JOIN ti AS a5 ON ((a3.c1 = a5.c1) AND (SELECT BOOL_AND (TRUE) FROM ti AS a6, GENERATE_SERIES (2, 10) AS a7 (c0) WHERE COALESCE (TRUE, TRUE))));
SELECT a1.c0 AS c0 FROM (GENERATE_SERIES (1, 1) AS a1 (c0) FULL JOIN JSON_TABLE (CASE WHEN ((ROW ((1.0 / 3)::float8, '_'::text) > ROW ('50'::float8, 'A'::text)) AND ('{"k": 0, "a": [3, 4, 5]}'::jsonb @@ 'exists($.a)')) THEN COALESCE (CASE WHEN TRUE THEN '{"k": 2, "a": [0]}'::jsonb ELSE '{"k": 0, "a": [3, 4, 5]}'::jsonb END, '{"k": 0, "a": [3, 4, 5]}'::jsonb) ELSE CASE WHEN (TRUE AND FALSE) THEN NULL::jsonb ELSE ('{"k": 0, "a": [3, 4, 5]}'::jsonb -> 0) END END, '$[*]' COLUMNS (c0 int PATH '$.k', c1 text PATH '$')) AS a2 ON (a1.c0 = a2.c0)) WHERE NULLIF (COALESCE (((NOT EXISTS (SELECT '1999-12-31 23:59:59.999999+05:30'::timestamptz AS c0, NULL::jsonb AS c1)) OR JSON_EXISTS (NULLIF (CASE WHEN TRUE THEN '{"k": 1, "a": [1, 2]}'::jsonb ELSE '{"k": 1, "a": [1, 2]}'::jsonb END, '{"k": -1, "a": [1, 2, 3]}'::jsonb), '$.k ? (@ > 0)')), COALESCE ((FALSE AND (a1.c0 BETWEEN '5'::int AND '19'::int)), (NOT ('{"k": -1, "a": [1, 2, 3]}'::jsonb <@ NULL::jsonb)))), (TRUE <= (((2.25::numeric + 0.0::numeric) + '15.4285714285714286'::numeric) > ('NaN'::numeric - 0.5::numeric)))) ORDER BY 1 DESC;
