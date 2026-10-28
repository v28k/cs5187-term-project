-- pgfuzz triage of 34bfff77ad1b: wrong_result via plan-variant
-- default plan:
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a3.c3)) - a3.c3 * 1)) c1 FROM (v0 AS a1 FULL JOIN tp AS a2 ON TRUE JOIN t3 AS a3 ON (a1.c0 = a3.c0)) WHERE TRUE;
-- plan variant no_join_reorder (must return the same rows):
SET join_collapse_limit = '1';
SET from_collapse_limit = '1';
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a3.c3)) - a3.c3 * 1)) c1 FROM (v0 AS a1 FULL JOIN tp AS a2 ON TRUE JOIN t3 AS a3 ON (a1.c0 = a3.c0)) WHERE TRUE;
RESET join_collapse_limit;
RESET from_collapse_limit;
