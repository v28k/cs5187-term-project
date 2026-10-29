-- pgfuzz failure 53f867a5bcc8 (wrong_result, signature strength: diff)
-- test case 26397 from random
-- SQLSTATE -: result differs under plan variant xversion: 2 rows by default, 1 rows with variant
-- failing statement: #1
SELECT c1 FROM t2 WHERE (c1 = 1.5);
