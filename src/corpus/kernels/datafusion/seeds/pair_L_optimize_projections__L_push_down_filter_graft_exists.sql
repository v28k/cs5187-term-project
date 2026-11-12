-- composition of rule kernels L:optimize_projections x L:push_down_filter (datafusion), template graft_exists
SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM (SELECT * FROM t3 WHERE EXISTS (SELECT 1 FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1) AS kb)) AS a1 WHERE a1.c1;
-- pgfuzz:check kernel:graft_exists SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1 WHERE a1.c1
