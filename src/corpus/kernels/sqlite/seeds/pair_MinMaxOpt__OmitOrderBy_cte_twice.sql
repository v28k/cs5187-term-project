-- composition of rule kernels MinMaxOpt x OmitOrderBy (sqlite), template cte_twice
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
WITH ka AS (SELECT '{"k": 0, "a": [3, 4, 5]}' AS c0, (- (SELECT MIN (a2.c0) FROM ti AS a2)) AS c1, CAST(10.0 AS NUMERIC) AS c2, 0 AS c3 FROM t0 AS a1), kb AS (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT '{"k": 0, "a": [3, 4, 5]}' AS c0, (- (SELECT MIN (a2.c0) FROM ti AS a2)) AS c1, CAST(10.0 AS NUMERIC) AS c2, 0 AS c3 FROM t0 AS a1) AS ka) + (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS kb)
