-- pgfuzz triage of b0171fcfb39a: wrong_result via plan-variant
-- default plan:
SELECT c0 FROM tl WHERE (c0 = 1);
-- plan variant index_scans (must return the same rows):
SET enable_seqscan = 'off';
SET enable_bitmapscan = 'off';
SELECT c0 FROM tl WHERE (c0 = 1);
RESET enable_seqscan;
RESET enable_bitmapscan;
