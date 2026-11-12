-- composition of rule kernels CoverIdxScan x OrderByIdxJoin (sqlite), template graft_union
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
SELECT '{"k": 1, "a": [1, 2]}' AS c0 FROM (SELECT * FROM tp UNION ALL SELECT * FROM tp WHERE (SELECT count(*) FROM (SELECT a.id, c.id FROM t a JOIN t c ORDER BY 1, 2) AS kb) < 0) AS a1 WHERE ((a1.c1, TRUE) <> (CASE WHEN FALSE THEN a1.c1 ELSE CONCAT_WS ('-', FALSE, (SELECT SUM (CAST(5e-324 AS REAL)) FROM t3 AS a2)) END, TRUE)) GROUP BY a1.c0, a1.c1;
-- pgfuzz:check kernel:graft_union SELECT '{"k": 1, "a": [1, 2]}' AS c0 FROM tp AS a1 WHERE ((a1.c1, TRUE) <> (CASE WHEN FALSE THEN a1.c1 ELSE CONCAT_WS ('-', FALSE, (SELECT SUM (CAST(5e-324 AS REAL)) FROM t3 AS a2)) END, TRUE)) GROUP BY a1.c0, a1.c1
