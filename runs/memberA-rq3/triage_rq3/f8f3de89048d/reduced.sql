-- pgfuzz triage of f8f3de89048d: wrong_result via cross-version
SELECT c0, count(*) AS n FROM t0 GROUP BY c0;
