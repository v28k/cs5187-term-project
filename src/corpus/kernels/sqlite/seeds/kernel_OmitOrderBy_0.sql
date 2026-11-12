-- rule kernel: OmitOrderBy (sqlite)
SELECT CAST('abc' AS TEXT) AS c0, 500 AS c1, '2024-02-29' AS c2 UNION SELECT a1.c2 AS c0, a1.c1 AS c1, '2024-12-31' AS c2 FROM (SELECT '1970-01-01' AS c0, 21 AS c1, CAST('{"k": 1}' AS TEXT) AS c2 ORDER BY 2, 3) AS a1 GROUP BY a1.c1, a1.c2;
