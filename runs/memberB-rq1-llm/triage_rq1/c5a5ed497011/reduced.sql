-- pgfuzz triage of c5a5ed497011: wrong_result via plan-variant
-- default plan:
(SELECT CORR (1.0 / 3,1.0 / 3) FROM tl);
-- plan variant partitionwise (must return the same rows):
SET enable_partitionwise_join = 'on';
SET enable_partitionwise_aggregate = 'on';
(SELECT CORR (1.0 / 3,1.0 / 3) FROM tl);
RESET enable_partitionwise_join;
RESET enable_partitionwise_aggregate;
