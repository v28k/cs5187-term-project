-- composition of rule kernels QueryFlattener x Transitive (sqlite), template graft_exists
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT '1999-12-31 23:59:59.999' AS c0, CAST(1.5 AS NUMERIC) AS c1, CAST(1000 AS INTEGER) AS c2 FROM (SELECT TRUE AS c0, 11 AS c1 FROM (SELECT * FROM t0 WHERE EXISTS (SELECT 1 FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb)) AS a1) AS a2;
-- pgfuzz:check kernel:graft_exists SELECT '1999-12-31 23:59:59.999' AS c0, CAST(1.5 AS NUMERIC) AS c1, CAST(1000 AS INTEGER) AS c2 FROM (SELECT TRUE AS c0, 11 AS c1 FROM t0 AS a1) AS a2
