-- pgfuzz failure 84e36fe21cff (internal_error, signature strength: message)
-- test case 1329 from grammar
-- SQLSTATE XX000: corrupt MVNDistinct entry
-- failing statement: #5
CREATE STATISTICS (NDISTINCT) ON c0, c1 FROM ti;
ANALYZE ti;
CREATE INDEX ON t1 USING BRIN (c0);
SELECT NULL::boolean AS c0 FROM v0 AS a1, LATERAL (SELECT '[1,10)'::int4range AS c0, LOWER (GREATEST (a3.c1, a3.c1)) AS c1 FROM t2 AS a2, (VALUES (1, 'a'::text), (2, NULL::text), (NULL::int, 'c'::text)) AS a3 (c0, c1)) AS a4 GROUP BY CUBE (a4.c1) UNION ALL SELECT (NOT (((INT4RANGE (LEAST (LENGTH (a5.c1), 0), GREATEST (GREATEST (NULL::int, NULL::int), 0)) * '[0,0]'::int4range) * INT4RANGE (LEAST (MAX (3) OVER (), 0), GREATEST ((10::bigint % 1000)::int, 0))) && INT4RANGE (LEAST (LOWER ('[0,0]'::int4range), 0), GREATEST ((2 % NULLIF ('8'::int, 0)), 0)))) AS c0 FROM ti AS a5, LATERAL (SELECT LPAD ('24'::text, 3, '*') AS c0, ((NULL::jsonb -> 'k') ->> 'a') AS c1) AS a6 GROUP BY ROLLUP (a6.c1, a5.c1);
SELECT MAX ((('{NULL}'::int[])[1])::bigint) OVER (PARTITION BY '0'::interval ORDER BY 54 NULLS FIRST, '{"k": 0, "a": [3, 4, 5]}'::jsonb) AS c0 FROM ti AS a1, LATERAL (SELECT ISEMPTY ('[1,10)'::int4range) AS c0, a1.c0 AS c1) AS a2 GROUP BY ROLLUP (a1.c0, a2.c1, a2.c0) HAVING BOOL_AND (a2.c0) UNION SELECT MIN (COUNT (*)) OVER (ORDER BY (100)::float8, 1.0::float8) AS c0 FROM tp AS a3, UNNEST ('{""}'::text[]) AS a4 (c0);
