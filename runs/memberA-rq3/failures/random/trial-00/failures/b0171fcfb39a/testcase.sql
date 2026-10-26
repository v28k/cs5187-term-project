-- pgfuzz failure b0171fcfb39a (wrong_result, signature strength: diff)
-- test case 32330 from random
-- SQLSTATE -: result differs under plan variant index_scans: 0 rows by default, 1 rows with variant
-- failing statement: #1
SELECT c0 FROM tl WHERE (c0 = 1);
