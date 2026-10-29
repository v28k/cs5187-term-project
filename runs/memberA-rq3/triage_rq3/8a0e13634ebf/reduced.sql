-- pgfuzz triage of 8a0e13634ebf: wrong_result via plan-variant
-- default plan:
SELECT CASE a2.c2 WHEN a1.c2 THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb WHEN a2.c2 THEN a1.c2 ELSE a2.c2 END FROM (t1 a1 JOIN t1 a2 USING (c0)) GROUP BY ROLLUP (a1.c2, a2.c2);
-- plan variant no_self_join_elim (must return the same rows):
SET enable_self_join_elimination = 'off';
SELECT CASE a2.c2 WHEN a1.c2 THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb WHEN a2.c2 THEN a1.c2 ELSE a2.c2 END FROM (t1 a1 JOIN t1 a2 USING (c0)) GROUP BY ROLLUP (a1.c2, a2.c2);
RESET enable_self_join_elimination;
