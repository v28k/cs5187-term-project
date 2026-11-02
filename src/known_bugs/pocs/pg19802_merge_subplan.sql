-- BUG #19802: MERGE into a partitioned table fails with "SubPlan found with no
-- parent plan". Found by the grammar fuzzer (internal error XX000).
-- Affected: 18, master; confirmed upstream, fix posted.
CREATE TABLE mp (a int, b text) PARTITION BY RANGE (a);
CREATE TABLE mp1 PARTITION OF mp FOR VALUES FROM (0) TO (10);
MERGE INTO mp t
USING (SELECT true AS c OFFSET 0) s ON t.a IS NULL
WHEN MATCHED THEN UPDATE SET b = (SELECT NULL WHERE s.c)
WHEN NOT MATCHED THEN INSERT VALUES (1, 'x');
