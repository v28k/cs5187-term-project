-- composition of rule kernels GroupByOrder x Transitive (sqlite), template union
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS ka UNION ALL SELECT 2 AS k FROM (WITH t(g, x) AS ( SELECT 1, 9007199254740994 ) SELECT NULL FROM t GROUP BY g ORDER BY g) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS ka) + (SELECT count(*) FROM (WITH t(g, x) AS ( SELECT 1, 9007199254740994 ) SELECT NULL FROM t GROUP BY g ORDER BY g) AS kb)
