-- composition of rule kernels OmitNoopJoin x OmitOrderBy (sqlite), template product
CREATE TABLE t2(a INTEGER, b INTEGER);
INSERT INTO t2 VALUES (1, 100);
INSERT INTO t2 VALUES (2, 200);
INSERT INTO t2 VALUES (3, 300);
CREATE TABLE names(name TEXT COLLATE NOCASE);
INSERT INTO names VALUES ('alice');
INSERT INTO names VALUES ('Bob');
INSERT INTO names VALUES ('CHARLIE');
INSERT INTO names VALUES ('dave');
SELECT count(*) FROM (WITH cte AS (SELECT name FROM names ORDER BY name) SELECT name FROM cte ORDER BY name COLLATE BINARY) AS ka CROSS JOIN (SELECT CAST(42.5 AS NUMERIC) AS c0 FROM (t3 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND a1.c1))) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (WITH cte AS (SELECT name FROM names ORDER BY name) SELECT name FROM cte ORDER BY name COLLATE BINARY) AS ka) * (SELECT count(*) FROM (SELECT CAST(42.5 AS NUMERIC) AS c0 FROM (t3 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND a1.c1))) AS kb)
