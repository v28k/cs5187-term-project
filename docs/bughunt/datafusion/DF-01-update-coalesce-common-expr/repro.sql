CREATE TABLE t (c0 INT, c1 VARCHAR);
INSERT INTO t VALUES (1, 'a'), (NULL, 'b');
UPDATE t SET c0 = COALESCE(c0, 0);
-- Error: UPDATE operation on table 't' caused by Schema error: No field named __common_expr_1. Valid fields are c0, c1.
-- expected: 2 rows updated; SELECT * FROM t ORDER BY c1 -> (1, 'a'), (0, 'b')
