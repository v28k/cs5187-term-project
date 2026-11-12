-- composition of rule kernels BalancedMerge x Coroutines (sqlite), template scalar_filter
SELECT count(*) FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS ka WHERE (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT FALSE AS c0, CAST('ß' AS TEXT) AS c1 UNION ALL SELECT TRUE AS c0, CAST('x%' AS TEXT) AS c1 FROM rc AS a1) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS ka
