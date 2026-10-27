-- pgfuzz triage of 83bdce4a0403: assertion via assertion
SELECT FROM t3 WHERE (c5 IN (SELECT c5 FROM v0 UNION ALL SELECT c5));
