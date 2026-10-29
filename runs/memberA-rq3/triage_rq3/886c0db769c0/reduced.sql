-- pgfuzz triage of 886c0db769c0: wrong_result via cross-version
SELECT a.c1 FROM t0 AS a JOIN t1 AS b ON (a.c0 = b.c0);
