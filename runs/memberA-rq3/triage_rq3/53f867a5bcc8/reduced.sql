-- pgfuzz triage of 53f867a5bcc8: wrong_result via cross-version
SELECT c1 FROM t2 WHERE (c1 = 1.5);
