-- pgfuzz triage of 294a0263ac67: wrong_result via plan-variant
-- default plan:
SELECT a1.c3, 0 FROM (t3 a1 LEFT JOIN t4 ON NULL) UNION SELECT '7 days', c1 FROM t4;
-- plan variant no_hashagg (must return the same rows):
SET enable_hashagg = 'off';
SELECT a1.c3, 0 FROM (t3 a1 LEFT JOIN t4 ON NULL) UNION SELECT '7 days', c1 FROM t4;
RESET enable_hashagg;
