-- pgfuzz failure 2fafe019f451 (assertion, signature strength: stack)
-- test case 252 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #5
CREATE TABLE c01 (a int, c bool);
INSERT INTO c01 SELECT x % 10, x % 10 < 5 FROM generate_series(1, 1000) x;
CREATE STATISTICS c01_deps (dependencies) ON a, (c IS TRUE) FROM c01;
ANALYZE c01;
SELECT count(*) FROM c01 WHERE a = 1 AND (c IS TRUE) AND (c IS TRUE);
