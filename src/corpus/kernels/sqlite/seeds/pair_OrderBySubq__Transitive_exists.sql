-- composition of rule kernels OrderBySubq x Transitive (sqlite), template exists
CREATE TABLE t (x INT);
INSERT INTO t VALUES (1);
SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS ka WHERE EXISTS (SELECT 1 FROM (SELECT TRUE AS c0, '{"k": 2, "a": [0]}' AS c1, a1.c0 AS c2 FROM (((tp AS a1 INNER JOIN v0 AS a2 ON (a1.c0 = a2.c0)) JOIN t0 AS a3 ON (a1.c0 = a3.c0)) JOIN t0 AS a4 ON ((a1.c1 = a4.c1) AND FALSE))) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT TRUE AS c0, '{"k": 2, "a": [0]}' AS c1, a1.c0 AS c2 FROM (((tp AS a1 INNER JOIN v0 AS a2 ON (a1.c0 = a2.c0)) JOIN t0 AS a3 ON (a1.c0 = a3.c0)) JOIN t0 AS a4 ON ((a1.c1 = a4.c1) AND FALSE))) AS kb) > 0 THEN (SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS ka) ELSE 0 END
