-- pgfuzz triage of 28a639c0f92c: wrong_result via cross-version
INSERT INTO t2 AS a1 (c2, c3) SELECT LAG ('1999-12-31 23:59:59.999999+05:30'::timestamptz) IGNORE NULLS OVER (ORDER BY 1) AS c0, '{a,b,c,d}'::text[] AS c1 FROM ti AS a2 ON CONFLICT DO NOTHING;
WITH rc(c0) AS (SELECT 1) SELECT FROM t2;
