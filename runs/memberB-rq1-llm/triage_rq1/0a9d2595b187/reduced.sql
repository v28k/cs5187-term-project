-- pgfuzz triage of 0a9d2595b187: wrong_result via plan-variant
-- default plan:
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a2.c3)) - a2.c3)) FROM (t4 a1 JOIN t3 AS a2 ON (a1.c0 = a2.c0));
-- plan variant mergejoin_only (must return the same rows):
SET enable_nestloop = 'off';
SET enable_hashjoin = 'off';
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a2.c3)) - a2.c3)) FROM (t4 a1 JOIN t3 AS a2 ON (a1.c0 = a2.c0));
RESET enable_nestloop;
RESET enable_hashjoin;
