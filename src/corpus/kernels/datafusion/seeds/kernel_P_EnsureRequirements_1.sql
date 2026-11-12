-- rule kernel: P:EnsureRequirements (datafusion)
SELECT LEAST (a1.c5, a1.c5) AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1;
