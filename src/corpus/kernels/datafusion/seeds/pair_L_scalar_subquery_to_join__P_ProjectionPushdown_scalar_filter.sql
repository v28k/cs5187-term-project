-- composition of rule kernels L:scalar_subquery_to_join x P:ProjectionPushdown (datafusion), template scalar_filter
SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka WHERE (SELECT count(*) FROM (SELECT a1.c0 AS c0 FROM tl AS a1 WHERE (SELECT BOOL_AND (TRUE) FROM ti AS a2 WHERE (NOT (NULL::boolean <= (16 IS DISTINCT FROM a1.c0)))) UNION SELECT 100 AS c0) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT 38 AS c0, ARRAY[1] AS c1 FROM v0 AS a1) AS ka
