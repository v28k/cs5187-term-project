-- rule kernel: Transitive (sqlite)
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f);
