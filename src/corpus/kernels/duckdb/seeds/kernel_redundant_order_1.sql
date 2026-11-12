-- rule kernel: redundant_order (duckdb)
SELECT '0'::interval AS c0, '1999-12-31'::date AS c1, 0.0::float8 AS c2 FROM ti AS a1 WHERE (SELECT BOOL_OR (a2.c0) FROM (SELECT FALSE AS c0 ORDER BY ALL) AS a2);
