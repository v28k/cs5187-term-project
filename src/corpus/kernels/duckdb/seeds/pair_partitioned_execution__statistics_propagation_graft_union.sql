-- composition of rule kernels partitioned_execution x statistics_propagation (duckdb), template graft_union
SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM (SELECT * FROM tl UNION ALL SELECT * FROM tl WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 100) SELECT 100 AS c0, 16 AS c1 UNION SELECT 27 AS c0, 17 AS c1) AS kb) < 0) AS a1;
-- pgfuzz:check kernel:graft_union SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1
