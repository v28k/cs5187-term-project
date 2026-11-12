-- composition of rule kernels Coroutines x OmitOrderBy (sqlite), template exists
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0 FROM tl AS a1 WHERE ((NULLIF (((SELECT JSON_GROUP_ARRAY (a2.c0 ORDER BY a2.c0) FROM v0 AS a2) ->> 'a'), a1.c1), FALSE) <> (a1.c1, TRUE)) GROUP BY a1.c0) AS ka WHERE EXISTS (SELECT 1 FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS kb) > 0 THEN (SELECT count(*) FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0 FROM tl AS a1 WHERE ((NULLIF (((SELECT JSON_GROUP_ARRAY (a2.c0 ORDER BY a2.c0) FROM v0 AS a2) ->> 'a'), a1.c1), FALSE) <> (a1.c1, TRUE)) GROUP BY a1.c0) AS ka) ELSE 0 END
