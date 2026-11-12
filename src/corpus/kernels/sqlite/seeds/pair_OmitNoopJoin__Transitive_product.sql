-- composition of rule kernels OmitNoopJoin x Transitive (sqlite), template product
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0 FROM (t0 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) UNION SELECT CAST('[1,10)' AS TEXT) AS c0) AS ka CROSS JOIN (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0 FROM (t0 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) UNION SELECT CAST('[1,10)' AS TEXT) AS c0) AS ka) * (SELECT count(*) FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb)
