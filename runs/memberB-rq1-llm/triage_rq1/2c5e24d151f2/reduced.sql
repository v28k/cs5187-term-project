-- pgfuzz triage of 2c5e24d151f2: wrong_result via plan-variant
-- default plan:
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a2.c3)) - a2.c3 * 1)) FROM (t1 a1 JOIN t3 a2 ON (a1.c0 = a2.c0)) WHERE a2.c1;
-- plan variant index_scans (must return the same rows):
SET enable_seqscan = 'off';
SET enable_bitmapscan = 'off';
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a2.c3)) - a2.c3 * 1)) FROM (t1 a1 JOIN t3 a2 ON (a1.c0 = a2.c0)) WHERE a2.c1;
RESET enable_seqscan;
RESET enable_bitmapscan;
