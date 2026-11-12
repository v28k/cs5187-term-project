-- rule kernel: GroupByOrder (sqlite)
WITH t(g, x) AS ( SELECT 1, '9007199254740994abc' ) SELECT NULL FROM t GROUP BY g ORDER BY g;
