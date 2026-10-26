-- pgfuzz failure 886c0db769c0 (wrong_result, signature strength: diff)
-- test case 26234 from random
-- SQLSTATE -: result differs under plan variant xversion: 378 rows by default, 189 rows with variant
-- failing statement: #1
SELECT a.c1 FROM t0 AS a JOIN t1 AS b ON (a.c0 = b.c0);
