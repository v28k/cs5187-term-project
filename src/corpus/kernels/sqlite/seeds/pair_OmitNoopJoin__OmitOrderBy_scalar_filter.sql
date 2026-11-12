-- composition of rule kernels OmitNoopJoin x OmitOrderBy (sqlite), template scalar_filter
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0 FROM (t0 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) UNION SELECT CAST('[1,10)' AS TEXT) AS c0) AS ka WHERE (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a1.c1 AS c0 FROM (t0 AS a1 LEFT JOIN t1 AS a2 ON ((a1.c0 = a2.c0) AND FALSE)) UNION SELECT CAST('[1,10)' AS TEXT) AS c0) AS ka
