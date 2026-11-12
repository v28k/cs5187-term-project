-- composition of rule kernels OrderBySubq x Transitive (sqlite), template union
CREATE TABLE t (x INT);
INSERT INTO t VALUES (1);
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT TRUE AS c0, '{"k": 2, "a": [0]}' AS c1, a1.c0 AS c2 FROM (((tp AS a1 INNER JOIN v0 AS a2 ON (a1.c0 = a2.c0)) JOIN t0 AS a3 ON (a1.c0 = a3.c0)) JOIN t0 AS a4 ON ((a1.c1 = a4.c1) AND FALSE))) AS ka UNION ALL SELECT 2 AS k FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT TRUE AS c0, '{"k": 2, "a": [0]}' AS c1, a1.c0 AS c2 FROM (((tp AS a1 INNER JOIN v0 AS a2 ON (a1.c0 = a2.c0)) JOIN t0 AS a3 ON (a1.c0 = a3.c0)) JOIN t0 AS a4 ON ((a1.c1 = a4.c1) AND FALSE))) AS ka) + (SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb)
