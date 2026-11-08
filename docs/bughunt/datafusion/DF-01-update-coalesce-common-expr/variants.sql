-- DF-01 variants: each UPDATE / DELETE fails on main bc86321 with "No field named __common_expr_N"
-- expected final table: (0, 'b', 0)
CREATE TABLE t (c0 INT, c1 VARCHAR, c2 BIGINT);
INSERT INTO t VALUES (1, 'a', 10), (NULL, 'b', 20);
UPDATE t SET c2 = COALESCE(c0, 0) + COALESCE(c0, 0);
UPDATE t SET c0 = COALESCE(c0, 0), c2 = COALESCE(c0, 0) * 2;
UPDATE t SET c1 = 'z' WHERE COALESCE(c0, 0) > 0 AND COALESCE(c0, 0) < 5;
DELETE FROM t WHERE COALESCE(c0, 0) > 0 AND COALESCE(c0, 0) < 5;
SELECT * FROM t ORDER BY c1;
