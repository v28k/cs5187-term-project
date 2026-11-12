-- composition of rule kernels L:optimize_projections x L:simplify_expressions (datafusion), template graft_union
SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM (SELECT * FROM t3 UNION ALL SELECT * FROM t3 WHERE (SELECT count(*) FROM (SELECT TRUE AS c0, 1.5::numeric AS c1) AS kb) < 0) AS a1;
-- pgfuzz:check kernel:graft_union SELECT a1.c5 AS c0, 10.0::float8 AS c1 FROM t3 AS a1
