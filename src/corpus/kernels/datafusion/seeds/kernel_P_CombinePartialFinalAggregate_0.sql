-- rule kernel: P:CombinePartialFinalAggregate (datafusion)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT MIN (CASE WHEN (SELECT BOOL_AND (FALSE) FROM tp AS a2) THEN a1.c0 ELSE a1.c0 END) AS c0, 5e-324::float8 AS c1 FROM t0 AS a1 GROUP BY CUBE (a1.c0);
