-- pgfuzz triage of 90ecfa669ba3: wrong_result via metamorphic:tlp_where
-- the two queries below must return the same rows (as a multiset):
SELECT '7 days'::interval AS c0 FROM t4 AS a1 INTERSECT ALL SELECT a2.c3 AS c0 FROM t3 AS a2 GROUP BY a2.c2, a2.c3, a2.c5 ORDER BY 1, 1;
((SELECT '7 days'::interval AS c0 FROM t4 AS a1 WHERE (('6.333333333333333'::float8 IN (SELECT (1.0 / 3)::float8 AS c0)))) UNION ALL (SELECT '7 days'::interval AS c0 FROM t4 AS a1 WHERE NOT (('6.333333333333333'::float8 IN (SELECT (1.0 / 3)::float8 AS c0)))) UNION ALL (SELECT '7 days'::interval AS c0 FROM t4 AS a1 WHERE (('6.333333333333333'::float8 IN (SELECT (1.0 / 3)::float8 AS c0))) IS NULL)) INTERSECT ALL SELECT a2.c3 AS c0 FROM t3 AS a2 GROUP BY a2.c2, a2.c3, a2.c5 ORDER BY 1, 1;
