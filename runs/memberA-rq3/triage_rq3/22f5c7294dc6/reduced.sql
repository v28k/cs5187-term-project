-- pgfuzz triage of 22f5c7294dc6: wrong_result via cross-version
INSERT INTO t2 AS a1 (c2, c3) SELECT LAG ('2024-02-29 12:34:56+00'::timestamptz) IGNORE NULLS OVER (ORDER BY 100) AS c0, '{a,b,c,d}'::text[] AS c1 FROM t1 AS a2 ON CONFLICT DO NOTHING;
WITH rc(c0) AS (SELECT 1) SELECT FROM t2;
