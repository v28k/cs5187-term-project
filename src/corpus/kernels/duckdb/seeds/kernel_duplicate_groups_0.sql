-- rule kernel: duplicate_groups (duckdb)
SELECT ((COUNT (DISTINCT a1.c1) % 1000)::int - 1) AS c0, a1.c1 AS c1, 'A'::text AS c2, 1::bigint AS c3 FROM tl AS a1 GROUP BY a1.c1;
