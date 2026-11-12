-- composition of rule kernels GroupByOrder x OrderBySubq (sqlite), template scalar_filter
CREATE TABLE t (x INT);
INSERT INTO t VALUES (1);
SELECT count(*) FROM (WITH t(g, x) AS ( SELECT 1, 9007199254740994 ) SELECT NULL FROM t GROUP BY g ORDER BY g) AS ka WHERE (SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (WITH t(g, x) AS ( SELECT 1, 9007199254740994 ) SELECT NULL FROM t GROUP BY g ORDER BY g) AS ka
