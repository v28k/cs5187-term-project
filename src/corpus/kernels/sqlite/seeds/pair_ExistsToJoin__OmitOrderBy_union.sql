-- composition of rule kernels ExistsToJoin x OmitOrderBy (sqlite), template union
CREATE TABLE t2(a INTEGER, b INTEGER);
INSERT INTO t2 VALUES (1, 100);
INSERT INTO t2 VALUES (2, 200);
INSERT INTO t2 VALUES (3, 300);
CREATE TABLE names(name TEXT COLLATE NOCASE);
INSERT INTO names VALUES ('alice');
INSERT INTO names VALUES ('Bob');
INSERT INTO names VALUES ('CHARLIE');
INSERT INTO names VALUES ('dave');
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0, '2024-01-01 00:00:00' AS c1 FROM t0 AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0, a2.c0 AS c1, a1.c1 AS c2 FROM t1 AS a2))) AS ka UNION ALL SELECT 2 AS k FROM (WITH cte AS (SELECT name FROM names ORDER BY name) SELECT name FROM cte ORDER BY name COLLATE BINARY) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0, '2024-01-01 00:00:00' AS c1 FROM t0 AS a1 WHERE (EXISTS (SELECT a1.c1 AS c0, a2.c0 AS c1, a1.c1 AS c2 FROM t1 AS a2))) AS ka) + (SELECT count(*) FROM (WITH cte AS (SELECT name FROM names ORDER BY name) SELECT name FROM cte ORDER BY name COLLATE BINARY) AS kb)
