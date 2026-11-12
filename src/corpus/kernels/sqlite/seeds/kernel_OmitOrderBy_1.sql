-- rule kernel: OmitOrderBy (sqlite)
CREATE TABLE sd(a INT, b INT);
INSERT INTO sd VALUES(1,3),(1,1),(1,2),(2,2),(2,1),(2,3);
WITH cte AS (SELECT b FROM sd ORDER BY b) SELECT * FROM cte ORDER BY b;
