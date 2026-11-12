-- composition of rule kernels CoverIdxScan x OrderByIdxJoin (sqlite), template product
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT count(*) FROM (SELECT '{"k": 1, "a": [1, 2]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, TRUE) <> (CASE WHEN FALSE THEN a1.c1 ELSE CONCAT_WS ('-', FALSE, (SELECT SUM (CAST(5e-324 AS REAL)) FROM t3 AS a2)) END, TRUE)) GROUP BY a1.c0, a1.c1) AS ka CROSS JOIN (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS kb;
-- pgfuzz:check kernel:product SELECT (SELECT count(*) FROM (SELECT '{"k": 1, "a": [1, 2]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, TRUE) <> (CASE WHEN FALSE THEN a1.c1 ELSE CONCAT_WS ('-', FALSE, (SELECT SUM (CAST(5e-324 AS REAL)) FROM t3 AS a2)) END, TRUE)) GROUP BY a1.c0, a1.c1) AS ka) * (SELECT count(*) FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS kb)
