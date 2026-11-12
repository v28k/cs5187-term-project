-- composition of rule kernels OmitOrderBy x Transitive (sqlite), template not_exists
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT '1999-12-31' AS c0, a1.c1 AS c1 FROM (SELECT CAST(1.0 AS REAL) AS c0, 500 AS c1 ORDER BY 2 DESC) AS a1 ORDER BY 2 DESC) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT '1999-12-31' AS c0, a1.c1 AS c1 FROM (SELECT CAST(1.0 AS REAL) AS c0, 500 AS c1 ORDER BY 2 DESC) AS a1 ORDER BY 2 DESC) AS ka) ELSE 0 END
