-- pgfuzz triage of 275e49476af8: wrong_result via plan-variant
CREATE VIEW n1 AS SELECT LAG (a1.c0) OVER (PARTITION BY a2.c0 ORDER BY 1::bigint DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS c0, ('A'::text || '[1,10)'::text) AS c1, '[1,10)'::text AS c2 FROM (ti AS a1 FULL JOIN t3 AS a2 ON (a1.c1 = a2.c5));
CREATE STATISTICS (MCV) ON c3, c2 FROM t1;
ANALYZE t1;
SELECT (((MIN (a1.c0) - ASCII (MD5 ('{"k": 1}'::text))) % 100) * (CASE WHEN (FALSE AND (ARRAY_LENGTH (ARRAY['1'::text], 1) IS NULL)) THEN (2 - COALESCE (7, (7 % NULLIF (15, 0)))) ELSE (ARRAY_POSITIONS ('{NULL,1}'::int[], 100))[5] END % 100)) AS c0, RANGE_INTERSECT_AGG (COALESCE ('[1,10)'::int4range, 'empty'::int4range)) AS c1, (LOWER (STRING_AGG (DISTINCT a2.c1, ',')))::text AS c2 FROM tp AS a1, ROWS FROM (GENERATE_SERIES (1, 3), UNNEST ('{a,b,c,d}'::text[])) AS a2 (c0, c1) GROUP BY GROUPING SETS ((a2.c1), (a1.c1), ());
-- default plan:
SELECT a1.c0 AS c0 FROM n1 AS a1 ORDER BY 1 NULLS LAST;
-- plan variant mergejoin_only (must return the same rows):
SET enable_nestloop = 'off';
SET enable_hashjoin = 'off';
SELECT a1.c0 AS c0 FROM n1 AS a1 ORDER BY 1 NULLS LAST;
RESET enable_nestloop;
RESET enable_hashjoin;
