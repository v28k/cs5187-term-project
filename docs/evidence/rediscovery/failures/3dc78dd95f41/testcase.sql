-- pgfuzz failure 3dc78dd95f41 (internal_error, signature strength: message)
-- test case 248 from grammar
-- SQLSTATE XX000: SubPlan found with no parent plan
-- failing statement: #3
CREATE TABLE mp (a int, b text) PARTITION BY RANGE (a);
CREATE TABLE mp1 PARTITION OF mp FOR VALUES FROM (0) TO (10);
MERGE INTO mp t
USING (SELECT true AS c OFFSET 0) s ON t.a IS NULL
WHEN MATCHED THEN UPDATE SET b = (SELECT NULL WHERE s.c)
WHEN NOT MATCHED THEN INSERT VALUES (1, 'x');
