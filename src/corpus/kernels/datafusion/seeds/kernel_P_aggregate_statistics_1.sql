-- rule kernel: P:aggregate_statistics (datafusion)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT '_'::text AS c0, (SELECT COUNT (*) FROM t1 AS a2) AS c1, 0::bigint AS c2 FROM t2 AS a1 INTERSECT SELECT 'a'::text AS c0, 1000::bigint AS c1, 100::bigint AS c2;
