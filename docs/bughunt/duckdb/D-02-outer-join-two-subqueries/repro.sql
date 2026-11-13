CREATE TABLE t (a INTEGER, b BOOLEAN);
CREATE TABLE u (c INTEGER);
INSERT INTO t VALUES (1, true), (6, false);
INSERT INTO u VALUES (1);

-- INTERNAL Error: Failed to bind column reference "a" [..] (bindings: {..})
SELECT * FROM t LEFT JOIN (SELECT 5 AS x) s ON ((SELECT 1) = ANY ([t.a + s.x]) OR 1 IN (SELECT c FROM u));
-- expected: (1, true, 5), (6, false, 5)

-- INTERNAL Error: Failed to bind column reference "x" [..]
SELECT * FROM t RIGHT JOIN (SELECT 5 AS x) s ON ((SELECT 1) = ANY ([t.a + s.x]) OR 1 IN (SELECT c FROM u));
-- expected: (1, true, 5), (6, false, 5)

-- same in MERGE (how the fuzzer hit it)
MERGE INTO t USING (SELECT 5 AS x) s ON ((SELECT 1) = ANY ([t.a + s.x]) OR 1 IN (SELECT c FROM u))
WHEN NOT MATCHED THEN INSERT VALUES (1, true);
-- expected: no error, 0 rows inserted (every source row matches)
