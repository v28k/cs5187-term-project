-- composition of rule kernels partitioned_execution x redundant_order (duckdb), template graft_scalar
SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM (SELECT * FROM tl WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT 'epoch'::timestamptz AS c0 FROM (SELECT 46 AS c0, 0 AS c1 ORDER BY ALL) AS a1 GROUP BY ROLLUP (a1.c1, a1.c0)) AS kb) >= 0) AS a1;
-- pgfuzz:check kernel:graft_scalar SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1
