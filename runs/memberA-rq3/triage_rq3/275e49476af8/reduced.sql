-- pgfuzz triage of 275e49476af8: wrong_result via plan-variant
CREATE VIEW n1 AS SELECT LAG (a1.c0) OVER (ORDER BY a2.c4) AS c0, a2.c5 AS c1, '[1,10)'::text AS c2 FROM (ti AS a1 FULL JOIN t3 AS a2 ON (a1.c1 = a2.c5));
-- default plan:
SELECT a1 FROM n1 a1;
-- plan variant mergejoin_only (must return the same rows):
SET enable_nestloop = 'off';
SET enable_hashjoin = 'off';
SELECT a1 FROM n1 a1;
RESET enable_nestloop;
RESET enable_hashjoin;
