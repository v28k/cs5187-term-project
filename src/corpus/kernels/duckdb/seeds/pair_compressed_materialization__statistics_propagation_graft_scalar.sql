-- composition of rule kernels compressed_materialization x statistics_propagation (duckdb), template graft_scalar
SELECT 20 AS c0, a1.c5 AS c1, 'A'::text AS c2, 1000::bigint AS c3 FROM (SELECT * FROM t3 WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT 100::bigint AS c0 UNION SELECT 10::bigint AS c0) AS kb) >= 0) AS a1 GROUP BY a1.c2, a1.c5;
-- pgfuzz:check kernel:graft_scalar SELECT 20 AS c0, a1.c5 AS c1, 'A'::text AS c2, 1000::bigint AS c3 FROM t3 AS a1 GROUP BY a1.c2, a1.c5
