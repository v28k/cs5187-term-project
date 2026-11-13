CREATE TABLE a (x INTEGER);
INSERT INTO a VALUES (1), (2);
-- each of these fails on 2.0.0 and on nightly 2.1.0.dev2610310630
-- with "Serialization Error: Cannot copy BoundSubqueryExpression"
SELECT min((SELECT [1])) FROM a;              -- expected [1]
SELECT max((SELECT {'k': x})) FROM a;         -- expected {'k': 2}
SELECT min((SELECT [x])) FROM a;              -- expected [1]
SELECT max((SELECT [x]), 1) FROM a;           -- expected [[2]]
SELECT min(CASE WHEN EXISTS (SELECT 1) THEN [x] END) FROM a;   -- expected [1]
