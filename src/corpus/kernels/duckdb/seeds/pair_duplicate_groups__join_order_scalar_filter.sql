-- composition of rule kernels duplicate_groups x join_order (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT 10::bigint AS c0 EXCEPT SELECT 10::bigint AS c0 FROM t4 AS a1 GROUP BY a1.c1, a1.c0, a1.c3) AS ka WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT 0 AS c0 UNION SELECT 7 AS c0) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 10::bigint AS c0 EXCEPT SELECT 10::bigint AS c0 FROM t4 AS a1 GROUP BY a1.c1, a1.c0, a1.c3) AS ka
