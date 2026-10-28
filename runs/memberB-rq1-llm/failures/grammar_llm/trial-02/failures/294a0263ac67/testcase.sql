-- pgfuzz failure 294a0263ac67 (wrong_result, signature strength: diff)
-- test case 14235 from grammar
-- SQLSTATE -: result differs under plan variant no_hashagg: 40 rows by default, 40 rows with variant
-- failing statement: #1
SELECT a1.c3 AS c0, 0::bigint AS c1 FROM (t3 AS a1 LEFT OUTER JOIN t4 AS a2 ON (a1.c0 = a2.c1)) WHERE a1.c1 UNION SELECT '7 days'::interval AS c0, 0::bigint AS c1 FROM t4 AS a3 WHERE JSON_EXISTS ('{"k": -1, "a": [1, 2, 3]}'::jsonb, '$.a[last]');
SELECT 0.5::float8 AS c0, '2024-01-01 15:00:00+00'::timestamptz AS c1 FROM (v0 AS a1 INNER JOIN ti AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) EXCEPT ALL SELECT 100.0::float8 AS c0, DATE_TRUNC ('month', '2024-02-29 12:34:56+00'::timestamptz) AS c1 FROM tp AS a3 ORDER BY 2 NULLS LAST, 1 DESC NULLS FIRST;
