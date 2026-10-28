-- pgfuzz triage of 9492d3bdd347: internal_error via plan-variant
SELECT 7 AS c0, a3.c0 AS c1, a3.c0 AS c2 FROM t4 AS a1, LATERAL (SELECT DISTINCT TRUE AS c0, a1.c1 AS c1, '60'::int AS c2 FROM v0 AS a2) AS a3 ORDER BY 2 DESC, 2 DESC;
SELECT MAX (a1.c1) OVER () AS c0 FROM (t1 AS a1 LEFT JOIN tp AS a2 ON (a1.c0 = a2.c0)) WHERE (a2.c1 IN (SELECT ('0'::text || a2.c1) AS c0)) UNION SELECT '1'::int AS c0 FROM tl AS a3 WHERE (FALSE NOT IN (SELECT (10 BETWEEN a5.c1 AND a4.c0) AS c0 FROM (t0 AS a4 LEFT JOIN t4 AS a5 ON (a4.c0 = a5.c0)) WHERE TRUE));
