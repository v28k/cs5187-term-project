-- pgfuzz failure dadb554fcc93 (wrong_result, signature strength: diff)
-- test case 472 from grammar
-- SQLSTATE -: metamorphic check expr:scalar_sub failed: 2 rows vs 2 rows
-- failing statement: #1
SELECT c, '(,)'::int4range @> c AS a, NOT ('empty'::int4range @> c) AS b FROM (VALUES (NULL::int), (1)) v(c);
