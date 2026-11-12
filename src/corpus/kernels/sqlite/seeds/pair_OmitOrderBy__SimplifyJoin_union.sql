-- composition of rule kernels OmitOrderBy x SimplifyJoin (sqlite), template union
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (SELECT 1 AS k FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka UNION ALL SELECT 2 AS k FROM (SELECT a1.c0 AS c0, CAST(0.5 AS REAL) AS c1, a2.c0 AS c2, '1970-01-01' AS c3 FROM (tp AS a1 FULL JOIN t4 AS a2 ON (a1.c0 = a2.c1)) WHERE (a2.c0 > 100)) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka) + (SELECT count(*) FROM (SELECT a1.c0 AS c0, CAST(0.5 AS REAL) AS c1, a2.c0 AS c2, '1970-01-01' AS c3 FROM (tp AS a1 FULL JOIN t4 AS a2 ON (a1.c0 = a2.c1)) WHERE (a2.c0 > 100)) AS kb)
