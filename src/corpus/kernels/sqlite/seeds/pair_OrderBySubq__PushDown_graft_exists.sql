-- composition of rule kernels OrderBySubq x PushDown (sqlite), template graft_exists
CREATE TABLE t (x INT);
INSERT INTO t VALUES (1);
SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM (SELECT * FROM t3 WHERE EXISTS (SELECT 1 FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb) OR NOT EXISTS (SELECT 1 FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb)) AS a2) - 54) > (-8)));
-- pgfuzz:check kernel:graft_exists SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))
