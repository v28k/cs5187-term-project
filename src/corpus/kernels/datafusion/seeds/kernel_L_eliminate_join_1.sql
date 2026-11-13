-- rule kernel: L:eliminate_join (datafusion)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT a2.c1 AS c0, a1.c1 AS c1 FROM (ti AS a1 JOIN (t2 AS a2 JOIN v0 AS a3 ON (a2.c0 = a3.n)) ON ((a1.c0 = a3.c0) AND FALSE));
