-- BUG #19793: range @> elem is folded to true/false for a NULL element when the
-- range is a constant empty or unbounded range. Found by the expr:scalar_sub
-- rewrite: wrapping the range in a sub-select blocks the folding.
-- Affected: 17, 18, master (open).
SELECT c, '(,)'::int4range @> c AS a, NOT ('empty'::int4range @> c) AS b FROM (VALUES (NULL::int), (1)) v(c);
-- pgfuzz:check expr:scalar_sub SELECT c, (SELECT '(,)'::int4range) @> c AS a, NOT ((SELECT 'empty'::int4range) @> c) AS b FROM (VALUES (NULL::int), (1)) v(c)
