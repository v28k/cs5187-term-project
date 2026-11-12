-- composition of rule kernels Coroutines x OmitOrderBy (sqlite), template not_exists
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT FALSE AS c0, CAST('ß' AS TEXT) AS c1 UNION ALL SELECT TRUE AS c0, CAST('x%' AS TEXT) AS c1 FROM rc AS a1) AS ka WHERE NOT EXISTS (SELECT 1 FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS kb) = 0 THEN (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT FALSE AS c0, CAST('ß' AS TEXT) AS c1 UNION ALL SELECT TRUE AS c0, CAST('x%' AS TEXT) AS c1 FROM rc AS a1) AS ka) ELSE 0 END
