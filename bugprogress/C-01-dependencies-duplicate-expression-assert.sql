-- C-01: assertion failure in dependencies_clauselist_selectivity()
-- when two clauses reference the same extended-statistics expression.
DROP TABLE IF EXISTS dt;
CREATE TABLE dt (a int, b int);
INSERT INTO dt SELECT x % 10, x % 10 FROM generate_series(1, 1000) x;
CREATE STATISTICS dt_deps (dependencies) ON a, (b + 1) FROM dt;
ANALYZE dt;
-- crashes an assert-enabled server:
EXPLAIN SELECT * FROM dt WHERE a = 1 AND (b + 1) = 2 AND (b + 1) IN (2, 3);

-- second form: the same BooleanTest twice (columns must be correlated so that
-- ANALYZE stores a dependency)
DROP TABLE IF EXISTS dt2;
CREATE TABLE dt2 (a int, c bool);
INSERT INTO dt2 SELECT x % 10, x % 10 < 5 FROM generate_series(1, 1000) x;
CREATE STATISTICS dt2_deps (dependencies) ON a, (c IS TRUE) FROM dt2;
ANALYZE dt2;
EXPLAIN SELECT * FROM dt2 WHERE a = 1 AND (c IS TRUE) AND (c IS TRUE);
