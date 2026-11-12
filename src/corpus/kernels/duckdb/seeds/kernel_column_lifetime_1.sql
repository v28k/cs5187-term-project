-- rule kernel: column_lifetime (duckdb)
SELECT AGE ((MAX ('1999-12-31 23:59:59.999999+05:30'::timestamptz) OVER (PARTITION BY 16) - '-1 month'::interval), DATE_TRUNC ('year', (SELECT MIN ('1999-12-31 23:59:59.999999+05:30'::timestamptz) FROM t4 AS a1))) AS c0, 45 AS c1, 40 AS c2;
