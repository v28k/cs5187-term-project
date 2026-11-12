-- composition of rule kernels OmitOrderBy x QueryFlattener (sqlite), template product
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka CROSS JOIN (SELECT '1999-12-31 23:59:59.999' AS c0, CAST(1.5 AS NUMERIC) AS c1, CAST(1000 AS INTEGER) AS c2 FROM (SELECT TRUE AS c0, 11 AS c1 FROM t0 AS a1) AS a2) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka) * (SELECT count(*) FROM (SELECT '1999-12-31 23:59:59.999' AS c0, CAST(1.5 AS NUMERIC) AS c1, CAST(1000 AS INTEGER) AS c2 FROM (SELECT TRUE AS c0, 11 AS c1 FROM t0 AS a1) AS a2) AS kb)
