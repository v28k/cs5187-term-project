-- pgfuzz triage of 1a3d32e70e0c: wrong_result via cross-version
INSERT INTO t2 AS a1 (c2, c3) SELECT LAG ('epoch'::timestamptz) IGNORE NULLS OVER (ORDER BY 2) AS c0, '{NULL}'::text[] AS c1 FROM v0 AS a2 ON CONFLICT DO NOTHING;
WITH rc AS (SELECT) SELECT FROM (SELECT FROM t2);
