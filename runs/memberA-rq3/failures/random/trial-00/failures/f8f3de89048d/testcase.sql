-- pgfuzz failure f8f3de89048d (wrong_result, signature strength: diff)
-- test case 26359 from random
-- SQLSTATE -: result differs under plan variant xversion: 19 rows by default, 19 rows with variant
-- failing statement: #1
SELECT c0, count(*) AS n FROM t0 GROUP BY c0;
