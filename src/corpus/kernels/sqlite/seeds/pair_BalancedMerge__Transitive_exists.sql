-- composition of rule kernels BalancedMerge x Transitive (sqlite), template exists
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1) AS ka WHERE EXISTS (SELECT 1 FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS kb) > 0 THEN (SELECT count(*) FROM (SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1) AS ka) ELSE 0 END
