-- composition of rule kernels OmitNoopJoin x OrderByIdxJoin (sqlite), template union
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS ka UNION ALL SELECT 2 AS k FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0 FROM (t0 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) UNION SELECT CAST('[1,10)' AS TEXT) AS c0) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS ka) + (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0 FROM (t0 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) UNION SELECT CAST('[1,10)' AS TEXT) AS c0) AS kb)
