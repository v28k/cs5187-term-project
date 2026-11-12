-- composition of rule kernels CoverIdxScan x OrderByIdxJoin (sqlite), template cte_twice
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
WITH ka AS (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2), kb AS (SELECT '{"k": 1, "a": [1, 2]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, TRUE) <> (CASE WHEN FALSE THEN a1.c1 ELSE CONCAT_WS ('-', FALSE, (SELECT SUM (CAST(5e-324 AS REAL)) FROM t3 AS a2)) END, TRUE)) GROUP BY a1.c0, a1.c1) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS ka) + (SELECT count(*) FROM (SELECT '{"k": 1, "a": [1, 2]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, TRUE) <> (CASE WHEN FALSE THEN a1.c1 ELSE CONCAT_WS ('-', FALSE, (SELECT SUM (CAST(5e-324 AS REAL)) FROM t3 AS a2)) END, TRUE)) GROUP BY a1.c0, a1.c1) AS kb)
