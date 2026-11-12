-- composition of rule kernels DistinctOpt x OmitOrderBy (sqlite), template not_exists
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN t2 AS a3 ON ((a1.c3 = a3.c1) AND FALSE))) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT DISTINCT a2.c0 AS c0 FROM ((t4 AS a1 JOIN t4 AS a2 ON (a1.c0 = a2.c0)) INNER JOIN t2 AS a3 ON ((a1.c3 = a3.c1) AND FALSE))) AS kb) = 0 THEN (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka) ELSE 0 END
