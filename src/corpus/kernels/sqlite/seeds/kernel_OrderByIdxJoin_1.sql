-- rule kernel: OrderByIdxJoin (sqlite)
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2;
