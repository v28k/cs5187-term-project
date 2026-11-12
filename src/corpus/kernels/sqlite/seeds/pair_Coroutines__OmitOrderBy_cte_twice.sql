-- composition of rule kernels Coroutines x OmitOrderBy (sqlite), template cte_twice
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
WITH ka AS (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0 FROM tl AS a1 WHERE ((NULLIF (((SELECT JSON_GROUP_ARRAY (a2.c0 ORDER BY a2.c0) FROM v0 AS a2) ->> 'a'), a1.c1), FALSE) <> (a1.c1, TRUE)) GROUP BY a1.c0), kb AS (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT '{"k": -1, "a": [1, 2, 3]}' AS c0 FROM tl AS a1 WHERE ((NULLIF (((SELECT JSON_GROUP_ARRAY (a2.c0 ORDER BY a2.c0) FROM v0 AS a2) ->> 'a'), a1.c1), FALSE) <> (a1.c1, TRUE)) GROUP BY a1.c0) AS ka) + (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS kb)
