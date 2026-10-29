-- pgfuzz triage of 255e08379e82: wrong_result via plan-variant
-- default plan:
SELECT JSONB_AGG (a3 ORDER BY NULL) FROM (tp JOIN (tp a2 FULL JOIN t4 a3 ON NULL) ON TRUE);
-- plan variant no_memoize_material (must return the same rows):
SET enable_memoize = 'off';
SET enable_material = 'off';
SELECT JSONB_AGG (a3 ORDER BY NULL) FROM (tp JOIN (tp a2 FULL JOIN t4 a3 ON NULL) ON TRUE);
RESET enable_memoize;
RESET enable_material;
