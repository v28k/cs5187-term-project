-- rule kernel: GroupByOrder (sqlite)
WITH TRUE AS ( SELECT 1 ) SELECT NULL FROM t GROUP BY g ORDER BY g;
