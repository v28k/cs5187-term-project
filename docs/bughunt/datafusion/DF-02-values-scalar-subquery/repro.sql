VALUES ((SELECT 1), 5);
-- Internal error: ScalarSubqueryExpr evaluated before the subquery was executed.
-- This issue was likely caused by a bug in DataFusion's code.
-- expected: one row (1, 5)

SELECT * FROM (VALUES ((SELECT min(x) FROM (VALUES (1), (2)) AS v(x)), 5)) AS t(a, b);
-- same error; expected (1, 5)
