-- rule kernel: grouping_sets (duckdb)
WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT TRUE AS c0, BOOL_AND (FALSE) AS c1, [NULL]::text[] AS c2 FROM rc AS a1 GROUP BY ROLLUP (a1.c0) UNION (SELECT FALSE AS c0, TRUE AS c1, []::text[] AS c2 UNION SELECT TRUE AS c0, TRUE AS c1, []::text[] AS c2);
