-- composition of rule kernels Coroutines x Transitive (sqlite), template union
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0 FROM tl AS a1 WHERE ((NULLIF (((SELECT JSON_GROUP_ARRAY (a2.c0 ORDER BY a2.c0) FROM v0 AS a2) ->> 'a'), a1.c1), FALSE) <> (a1.c1, TRUE)) GROUP BY a1.c0) AS ka UNION ALL SELECT 2 AS k FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0 FROM tl AS a1 WHERE ((NULLIF (((SELECT JSON_GROUP_ARRAY (a2.c0 ORDER BY a2.c0) FROM v0 AS a2) ->> 'a'), a1.c1), FALSE) <> (a1.c1, TRUE)) GROUP BY a1.c0) AS ka) + (SELECT count(*) FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb)
