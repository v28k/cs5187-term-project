-- composition of rule kernels OrderByIdxJoin x OrderBySubq (sqlite), template union
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT TRUE AS c0, TRUE AS c1 FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 UNION SELECT CAST(1.5 AS NUMERIC) AS c0) AS a1 GROUP BY a1.c0) AS ka UNION ALL SELECT 2 AS k FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT TRUE AS c0, TRUE AS c1 FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 UNION SELECT CAST(1.5 AS NUMERIC) AS c0) AS a1 GROUP BY a1.c0) AS ka) + (SELECT count(*) FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS kb)
