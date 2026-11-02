-- C-01 (pgsql-bugs, 27 Oct 2026): dependencies_clauselist_selectivity() fails
-- an assertion when two clauses reference the same extended-statistics
-- expression. Affected: master. Detected by the assertion oracle.
CREATE TABLE c01 (a int, c bool);
INSERT INTO c01 SELECT x % 10, x % 10 < 5 FROM generate_series(1, 1000) x;
CREATE STATISTICS c01_deps (dependencies) ON a, (c IS TRUE) FROM c01;
ANALYZE c01;
SELECT count(*) FROM c01 WHERE a = 1 AND (c IS TRUE) AND (c IS TRUE);
