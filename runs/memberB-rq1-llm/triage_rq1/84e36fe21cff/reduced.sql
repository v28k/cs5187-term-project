-- pgfuzz triage of 84e36fe21cff: internal_error via metamorphic:expr
CREATE STATISTICS (NDISTINCT) ON c0, c1 FROM ti;
ANALYZE ti;
-- the two queries below must return the same rows (as a multiset):
SELECT NULL FROM ti a1, LATERAL (SELECT a1.c0) a2 GROUP BY ROLLUP (a1.c0, a2);
SELECT NULL FROM ti a1, LATERAL (SELECT (SELECT (a1.c0))) a2 GROUP BY ROLLUP (a1.c0, a2);
