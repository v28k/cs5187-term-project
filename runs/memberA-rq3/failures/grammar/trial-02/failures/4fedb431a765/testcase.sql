-- pgfuzz failure 4fedb431a765 (internal_error, signature strength: message)
-- test case 4400 from grammar
-- SQLSTATE XX000: could not find pathkey item to sort
-- failing statement: #2
CREATE INDEX ON t1 USING GIST (c3);
INSERT INTO tl AS a1 (c1) SELECT (a2.c1 COLLATE "C") AS c0 FROM (tl AS a2 LEFT JOIN t1 AS a3 ON ((a2.c0 = a3.c0) AND FALSE)) WHERE (FALSE > TRUE) UNION (SELECT MD5 (CASE WHEN TRUE THEN TO_CHAR (42.5::numeric, 'FM999990.00') ELSE NULLIF (LOWER ('_'::text), COALESCE ((a4.c0)::text, ' '::text)) END) AS c0 FROM v0 AS a4 WHERE FALSE GROUP BY ROLLUP (a4.c0, a4.n) INTERSECT ALL SELECT COALESCE (('_'::text || '_'::text), (('{}'::jsonb ->> (-1)))::text) AS c0 FROM tl AS a5 GROUP BY a5.c0) ON CONFLICT DO NOTHING;
