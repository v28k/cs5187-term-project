-- pgfuzz triage of f03cf100a032: wrong_result via plan-variant
-- default plan:
SELECT * FROM tl LIM;
-- plan variant no_eager_agg (must return the same rows):
SET enable_eager_aggregate = 'off';
SELECT * FROM tl LIM;
RESET enable_eager_aggregate;
