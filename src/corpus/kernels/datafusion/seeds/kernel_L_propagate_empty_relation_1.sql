-- rule kernel: L:propagate_empty_relation (datafusion)
SELECT 'abc'::text AS c0 FROM t1 AS a1 WHERE FALSE;
