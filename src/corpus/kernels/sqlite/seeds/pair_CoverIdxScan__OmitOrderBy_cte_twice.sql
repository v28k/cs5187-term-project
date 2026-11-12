-- composition of rule kernels CoverIdxScan x OmitOrderBy (sqlite), template cte_twice
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
WITH ka AS (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b), kb AS (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT FALSE AS c0, CAST('abc' AS TEXT) AS c1 FROM t0 AS a1 UNION ALL SELECT FALSE AS c0, CAST('NaN' AS TEXT) AS c1) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka) + (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT FALSE AS c0, CAST('abc' AS TEXT) AS c1 FROM t0 AS a1 UNION ALL SELECT FALSE AS c0, CAST('NaN' AS TEXT) AS c1) AS kb)
