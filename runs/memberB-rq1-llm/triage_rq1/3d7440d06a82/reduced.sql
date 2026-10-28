-- pgfuzz triage of 3d7440d06a82: wrong_result via plan-variant
-- default plan:
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a3.c3)) - a3.c3 * 1)) FROM (t4 a1 JOIN t3 AS a3 ON (a1.c0 = a3.c0));
-- plan variant mergejoin_only (must return the same rows):
SET enable_nestloop = 'off';
SET enable_hashjoin = 'off';
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a3.c3)) - a3.c3 * 1)) FROM (t4 a1 JOIN t3 AS a3 ON (a1.c0 = a3.c0));
RESET enable_nestloop;
RESET enable_hashjoin;
