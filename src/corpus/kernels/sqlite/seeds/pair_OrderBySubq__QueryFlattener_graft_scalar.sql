-- composition of rule kernels OrderBySubq x QueryFlattener (sqlite), template graft_scalar
CREATE TABLE t (x INT);
INSERT INTO t VALUES (1);
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a2.c1 AS c0, CAST('abc' AS TEXT) AS c1 FROM (SELECT CAST(1.5 AS NUMERIC) AS c0, FALSE AS c1, '{"k": 1, "a": [1, 2]}' AS c2 FROM (SELECT * FROM t0 WHERE (SELECT count(*) FROM (WITH t AS (SELECT 1 UNION SELECT 2) SELECT * FROM t ORDER BY 1) AS kb) >= 0) AS a1) AS a2 UNION ALL SELECT TRUE AS c0, CAST('abc' AS TEXT) AS c1;
-- pgfuzz:check kernel:graft_scalar WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a2.c1 AS c0, CAST('abc' AS TEXT) AS c1 FROM (SELECT CAST(1.5 AS NUMERIC) AS c0, FALSE AS c1, '{"k": 1, "a": [1, 2]}' AS c2 FROM t0 AS a1) AS a2 UNION ALL SELECT TRUE AS c0, CAST('abc' AS TEXT) AS c1
