-- composition of rule kernels OrderBySubq x PushDown (sqlite), template product
CREATE TABLE t (x INT);
INSERT INTO t VALUES (1);
SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS ka CROSS JOIN (SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS ka) * (SELECT count(*) FROM (SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))) AS kb)
