-- composition of rule kernels BloomFilter x OmitOrderBy (sqlite), template not_exists
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT '{"k": 2, "a": [0]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, CASE WHEN FALSE THEN TRUE ELSE (CAST(1 AS INTEGER) IN (SELECT CAST(100 AS INTEGER) AS c0)) END) <> (a1.c1, TRUE)) GROUP BY a1.c0, a1.c1) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT '{"k": 2, "a": [0]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, CASE WHEN FALSE THEN TRUE ELSE (CAST(1 AS INTEGER) IN (SELECT CAST(100 AS INTEGER) AS c0)) END) <> (a1.c1, TRUE)) GROUP BY a1.c0, a1.c1) AS kb) = 0 THEN (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka) ELSE 0 END
