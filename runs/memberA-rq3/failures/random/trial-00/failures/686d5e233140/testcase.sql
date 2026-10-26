-- pgfuzz failure 686d5e233140 (wrong_result, signature strength: diff)
-- test case 26050 from random
-- SQLSTATE -: result differs under plan variant xversion: 30 rows by default, 30 rows with variant
-- failing statement: #1
SELECT * FROM t2;
