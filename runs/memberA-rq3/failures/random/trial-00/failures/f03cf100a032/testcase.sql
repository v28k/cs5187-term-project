-- pgfuzz failure f03cf100a032 (wrong_result, signature strength: diff)
-- test case 31807 from random
-- SQLSTATE -: result differs under plan variant no_eager_agg: 0 rows by default, 80 rows with variant
-- failing statement: #1
SELECT * FROM tl LIM;
