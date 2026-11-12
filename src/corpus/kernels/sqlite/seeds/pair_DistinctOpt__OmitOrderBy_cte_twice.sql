-- composition of rule kernels DistinctOpt x OmitOrderBy (sqlite), template cte_twice
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
WITH ka AS (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b), kb AS (SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN t2 AS a3 ON ((a1.c3 = a3.c1) AND FALSE))) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka) + (SELECT count(*) FROM (SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN t2 AS a3 ON ((a1.c3 = a3.c1) AND FALSE))) AS kb)
