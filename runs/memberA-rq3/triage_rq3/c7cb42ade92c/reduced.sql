-- pgfuzz triage of c7cb42ade92c: wrong_result via cross-version
INSERT INTO t2 AS a1 (c2, c3) SELECT LAG (a2.c2) IGNORE NULLS OVER (ORDER BY 16) AS c0, a2.c3 AS c1 FROM t2 AS a2 ON CONFLICT DO NOTHING;
WITH rc(c0) AS (SELECT 1) SELECT FROM (SELECT FROM (t2 a1 RIGHT JOIN t2 ON NULL));
