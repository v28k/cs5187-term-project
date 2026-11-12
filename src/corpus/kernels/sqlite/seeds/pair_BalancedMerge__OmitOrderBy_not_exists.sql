-- composition of rule kernels BalancedMerge x OmitOrderBy (sqlite), template not_exists
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka WHERE NOT EXISTS (SELECT 1 FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS kb);
-- pgfuzz:check kernel:not_exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT NULL UNION SELECT 1 UNION SELECT 2 UNION SELECT NULL) AS kb) = 0 THEN (SELECT count(*) FROM (WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b) AS ka) ELSE 0 END
