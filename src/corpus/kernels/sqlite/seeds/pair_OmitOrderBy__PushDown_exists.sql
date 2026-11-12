-- composition of rule kernels OmitOrderBy x PushDown (sqlite), template exists
CREATE TABLE t2(a INTEGER, b INTEGER);
INSERT INTO t2 VALUES (1, 100);
INSERT INTO t2 VALUES (2, 200);
INSERT INTO t2 VALUES (3, 300);
CREATE TABLE names(name TEXT COLLATE NOCASE);
INSERT INTO names VALUES ('alice');
INSERT INTO names VALUES ('Bob');
INSERT INTO names VALUES ('CHARLIE');
INSERT INTO names VALUES ('dave');
SELECT count(*) FROM (SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))) AS ka WHERE EXISTS (SELECT 1 FROM (WITH cte AS (SELECT name FROM names ORDER BY name) SELECT name FROM cte ORDER BY name COLLATE BINARY) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (WITH cte AS (SELECT name FROM names ORDER BY name) SELECT name FROM cte ORDER BY name COLLATE BINARY) AS kb) > 0 THEN (SELECT count(*) FROM (SELECT CAST('A' AS TEXT) AS c0 FROM v0 AS a1 WHERE (NOT (((SELECT MIN (a2.c0) FROM t3 AS a2) - 54) > (-8)))) AS ka) ELSE 0 END
