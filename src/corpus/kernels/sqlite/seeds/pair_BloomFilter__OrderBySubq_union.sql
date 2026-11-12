-- composition of rule kernels BloomFilter x OrderBySubq (sqlite), template union
CREATE TABLE t (x INT);
INSERT INTO t VALUES (1);
SELECT count(*) FROM (SELECT 1 AS k FROM (SELECT '{"k": 2, "a": [0]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, CASE WHEN FALSE THEN TRUE ELSE (CAST(1 AS INTEGER) IN (SELECT CAST(100 AS INTEGER) AS c0)) END) <> (a1.c1, TRUE)) GROUP BY a1.c0, a1.c1) AS ka UNION ALL SELECT 2 AS k FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb) AS u;
-- pgfuzz:check kernel:union SELECT (SELECT count(*) FROM (SELECT '{"k": 2, "a": [0]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, CASE WHEN FALSE THEN TRUE ELSE (CAST(1 AS INTEGER) IN (SELECT CAST(100 AS INTEGER) AS c0)) END) <> (a1.c1, TRUE)) GROUP BY a1.c0, a1.c1) AS ka) + (SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb)
