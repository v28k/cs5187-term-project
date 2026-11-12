-- composition of rule kernels OrderByIdxJoin x Transitive (sqlite), template not_exists
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT TRUE AS c0, '{"k": 2, "a": [0]}' AS c1, a1.c0 AS c2 FROM (((tp AS a1 INNER JOIN v0 AS a2 ON (a1.c0 = a2.c0)) JOIN t0 AS a3 ON (a1.c0 = a3.c0)) JOIN t0 AS a4 ON ((a1.c1 = a4.c1) AND FALSE))) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT TRUE AS c0, '{"k": 2, "a": [0]}' AS c1, a1.c0 AS c2 FROM (((tp AS a1 INNER JOIN v0 AS a2 ON (a1.c0 = a2.c0)) JOIN t0 AS a3 ON (a1.c0 = a3.c0)) JOIN t0 AS a4 ON ((a1.c1 = a4.c1) AND FALSE))) AS kb) = 0 THEN (SELECT count(*) FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS ka) ELSE 0 END
