-- composition of rule kernels MinMaxOpt x OmitOrderBy (sqlite), template scalar_filter
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka WHERE (SELECT count(*) FROM (SELECT '{"k": 0, "a": [3, 4, 5]}' AS c0, (- (SELECT MIN (a2.c0) FROM ti AS a2)) AS c1, CAST(10.0 AS NUMERIC) AS c2, 0 AS c3 FROM t0 AS a1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka
