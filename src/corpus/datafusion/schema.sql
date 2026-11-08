-- Schema of the DataFusion target: the shared corpus schema without jsonb, ranges, partitions,
-- RLS and indexes (DataFusion has none); every test case starts from a fresh session with this state.
CREATE TABLE t0 (c0 INT, c1 VARCHAR, c2 DOUBLE);
CREATE TABLE t1 (c0 INT NOT NULL, c1 INT);
CREATE TABLE t2 (c0 BIGINT, c1 DECIMAL(10, 2), c2 TIMESTAMP WITH TIME ZONE, c3 VARCHAR[]);
CREATE TABLE t3 (c0 INT NOT NULL, c1 BOOLEAN, c2 DATE, c3 INTERVAL, c4 INT[], c5 VARCHAR);
CREATE TABLE t4 (c0 INT, c3 DECIMAL(18, 3));
CREATE TABLE tp (c0 INT NOT NULL, c1 VARCHAR);
CREATE TABLE tl (c0 INT, c1 VARCHAR);
CREATE TABLE ti (c0 INT, c1 VARCHAR);
INSERT INTO t0 SELECT CAST(value % 17 AS INT) AS x0, md5(CAST(value AS VARCHAR)) AS x1, value / 3.0 AS x2 FROM generate_series(1, 200);
INSERT INTO t0 VALUES (NULL, NULL, NULL), (0, '', 0.0), (-1, 'x', -1.5);
INSERT INTO t1 SELECT CAST(value AS INT) AS x0, CAST(NULLIF(value - 1, 0) AS INT) AS x1 FROM generate_series(1, 50);
INSERT INTO t2 SELECT value AS x0, CAST(value * 1.5 AS DECIMAL(10, 2)) AS x1, TIMESTAMP '2024-01-01 00:00:00+00' + CAST(CAST(value * 5 AS VARCHAR) || ' hours' AS INTERVAL) AS x2, [CAST(value AS VARCHAR), 'a'] AS x3 FROM generate_series(1, 30);
INSERT INTO t3 SELECT CAST(value % 23 AS INT) AS x0, CASE WHEN value % 5 = 0 THEN NULL ELSE value % 2 = 0 END AS x1, DATE '2024-01-01' + CAST(value AS INT) AS x2, CAST(CAST(value * 7 AS VARCHAR) || ' hours' AS INTERVAL) AS x3, [CAST(value AS INT), CAST(value % 4 AS INT), NULL] AS x4, chr(CAST(65 + value % 26 AS INT)) AS x5 FROM generate_series(1, 100);
INSERT INTO t4 SELECT CAST(CASE WHEN value % 9 = 0 THEN NULL ELSE value % 31 END AS INT) AS x0, CAST(value / 7.0 AS DECIMAL(18, 3)) AS x1 FROM generate_series(1, 120);
INSERT INTO tp SELECT CAST(value AS INT) AS x0, CAST(value AS VARCHAR) AS x1 FROM generate_series(1, 200);
INSERT INTO tl SELECT CAST(value AS INT) AS x0, CASE value % 4 WHEN 0 THEN 'a' WHEN 1 THEN 'b' WHEN 2 THEN 'c' END AS x1 FROM generate_series(1, 80);
INSERT INTO ti SELECT CAST(value AS INT) AS x0, CAST(value AS VARCHAR) AS x1 FROM generate_series(1, 40);
CREATE VIEW v0 AS SELECT c0, count(*) AS n FROM t0 GROUP BY c0;
