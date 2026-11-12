-- composition of rule kernels BalancedMerge x OmitOrderBy (sqlite), template cte_twice
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
WITH ka AS (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b), kb AS (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka) + (SELECT count(*) FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS kb)
