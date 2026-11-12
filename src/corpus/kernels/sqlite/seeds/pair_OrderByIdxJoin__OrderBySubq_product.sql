-- composition of rule kernels OrderByIdxJoin x OrderBySubq (sqlite), template product
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT TRUE AS c0, TRUE AS c1 FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 UNION SELECT CAST(1.5 AS NUMERIC) AS c0) AS a1 GROUP BY a1.c0) AS ka CROSS JOIN (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT TRUE AS c0, TRUE AS c1 FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 UNION SELECT CAST(1.5 AS NUMERIC) AS c0) AS a1 GROUP BY a1.c0) AS ka) * (SELECT count(*) FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS kb)
