-- rule kernel: L:eliminate_duplicated_expr (datafusion)
SELECT 10.0::float8 AS c0 UNION SELECT 0.5::float8 AS c0 ORDER BY 1, 1;
