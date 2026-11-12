-- rule kernel: L:scalar_subquery_to_join (datafusion)
SELECT a1.c0 AS c0 FROM tl AS a1 WHERE (SELECT BOOL_AND (TRUE) FROM ti AS a2 WHERE (NOT (NULL::boolean <= (16 IS DISTINCT FROM a1.c0)))) UNION SELECT 100 AS c0;
