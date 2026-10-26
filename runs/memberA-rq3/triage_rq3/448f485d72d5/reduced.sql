-- pgfuzz triage of 448f485d72d5: assertion via assertion
SELECT FROM t4 a1 WHERE (c0 <> ANY (SELECT a1.c1 UNION ALL SELECT a1.c0 FROM v0) AND FALSE);
