-- rule kernel: L:optimize_unions (datafusion)
SELECT '%'::text AS c0 INTERSECT (SELECT 'a'::text AS c0 UNION (SELECT '[1,10)'::text AS c0 UNION SELECT 'x%'::text AS c0));
