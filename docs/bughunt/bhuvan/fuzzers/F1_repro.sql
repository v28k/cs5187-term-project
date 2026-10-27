-- F1: NOT IN -> anti-join conversion ignores a NULL-producing implicit cast
-- applied to the sub-select's output column.
\pset null '<NULL>'
CREATE FUNCTION i2t(int) RETURNS text IMMUTABLE STRICT LANGUAGE sql
  AS $$ SELECT CASE WHEN $1 <> 0 THEN format('%s', $1) END $$;   -- NULL for 0
CREATE CAST (int AS text) WITH FUNCTION i2t(int) AS IMPLICIT;

CREATE TABLE o (t text NOT NULL);
CREATE TABLE s (i int NOT NULL);
INSERT INTO o VALUES ('1');
INSERT INTO s VALUES (0);

-- Ground truth: '1' = i2t(0) is '1' = NULL, so NOT IN yields NULL
SELECT t, t NOT IN (SELECT i FROM s) AS not_in FROM o;

-- Expected: 0 rows.  Each join method:
SELECT t FROM o WHERE t NOT IN (SELECT i FROM s);
SET enable_mergejoin = off;
SELECT t FROM o WHERE t NOT IN (SELECT i FROM s);
SET enable_hashjoin = off;
SELECT t FROM o WHERE t NOT IN (SELECT i FROM s);
RESET ALL;

-- multi-column form (expected 0 rows)
CREATE TABLE o2 (t text NOT NULL, k int NOT NULL);
CREATE TABLE s2 (i int NOT NULL, k int NOT NULL);
INSERT INTO o2 VALUES ('1', 1);
INSERT INTO s2 VALUES (0, 1);
SELECT * FROM o2 WHERE (t, k) NOT IN (SELECT i, k FROM s2);

-- correlated (LATERAL) form (expected 0 rows)
SELECT * FROM o2 WHERE t NOT IN (SELECT s2.i FROM s2 WHERE s2.k = o2.k);

EXPLAIN (COSTS OFF) SELECT t FROM o WHERE t NOT IN (SELECT i FROM s);
