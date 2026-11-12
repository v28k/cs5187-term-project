-- composition of rule kernels CoverIdxScan x OmitOrderBy (sqlite), template scalar_filter
CREATE TABLE t2(a INTEGER, b INTEGER);
INSERT INTO t2 VALUES (1, 100);
INSERT INTO t2 VALUES (2, 200);
INSERT INTO t2 VALUES (3, 300);
CREATE TABLE names(name TEXT COLLATE NOCASE);
INSERT INTO names VALUES ('alice');
INSERT INTO names VALUES ('Bob');
INSERT INTO names VALUES ('CHARLIE');
INSERT INTO names VALUES ('dave');
SELECT count(*) FROM (WITH cte AS (SELECT name FROM names ORDER BY name) SELECT name FROM cte ORDER BY name COLLATE BINARY) AS ka WHERE (SELECT count(*) FROM (SELECT '{"k": 1, "a": [1, 2]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, TRUE) <> (CASE WHEN FALSE THEN a1.c1 ELSE CONCAT_WS ('-', FALSE, (SELECT SUM (CAST(5e-324 AS REAL)) FROM t3 AS a2)) END, TRUE)) GROUP BY a1.c0, a1.c1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (WITH cte AS (SELECT name FROM names ORDER BY name) SELECT name FROM cte ORDER BY name COLLATE BINARY) AS ka
