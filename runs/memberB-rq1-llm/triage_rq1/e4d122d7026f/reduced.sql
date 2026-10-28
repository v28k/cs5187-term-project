-- pgfuzz triage of e4d122d7026f: wrong_result via plan-variant
-- default plan:
SELECT JSONB_AGG (a3 ORDER BY NULL) FROM (tp a1 JOIN (t4 JOIN t4 a3 ON TRUE) ON (a1.c0 = a3.c1));
-- plan variant no_join_reorder (must return the same rows):
SET join_collapse_limit = '1';
SET from_collapse_limit = '1';
SELECT JSONB_AGG (a3 ORDER BY NULL) FROM (tp a1 JOIN (t4 JOIN t4 a3 ON TRUE) ON (a1.c0 = a3.c1));
RESET join_collapse_limit;
RESET from_collapse_limit;
