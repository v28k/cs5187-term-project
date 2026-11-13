-- rule kernel: P:EnsureRequirements (datafusion)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT ' '::text AS c0, 3 AS c1 ORDER BY 1;
