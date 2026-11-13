-- rule kernel: OmitOrderBy (sqlite)
SELECT FALSE AS c0, '{}' AS c1 FROM (SELECT '2024-12-31' AS c0, CAST('ß' AS TEXT) AS c1, 100 AS c2 FROM t2 AS a1 ORDER BY 2) AS a2 ORDER BY 2;
