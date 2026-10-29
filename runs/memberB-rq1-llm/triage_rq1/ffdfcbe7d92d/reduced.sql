-- pgfuzz triage of ffdfcbe7d92d: wrong_result via plan-variant
-- default plan:
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a3.c3)) - a3.c3 * 1)) FROM (t4 a1 JOIN t4 AS a2 ON (a1.c0 = a2.c1) JOIN t3 AS a3 ON (a1.c0 = a3.c0));
-- plan variant nestloop_only (must return the same rows):
SET enable_hashjoin = 'off';
SET enable_mergejoin = 'off';
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a3.c3)) - a3.c3 * 1)) FROM (t4 a1 JOIN t4 AS a2 ON (a1.c0 = a2.c1) JOIN t3 AS a3 ON (a1.c0 = a3.c0));
RESET enable_hashjoin;
RESET enable_mergejoin;
