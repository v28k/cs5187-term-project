-- H-A12: NOT IN -> anti-join conversion checks the subquery's output column
-- and the outer expression for non-nullability, but the test expression's
-- Param side may carry an implicit coercion that can yield NULL from a
-- non-null input.  NOT IN must then return NULL (row filtered), whereas an
-- anti-join returns the row.
\pset null '<NULL>'
CREATE FUNCTION int_to_text_nullzero(int) RETURNS text
  LANGUAGE sql IMMUTABLE STRICT
  AS $$ SELECT CASE WHEN $1 = 0 THEN NULL ELSE format('%s', $1) END $$;
CREATE CAST (int AS text) WITH FUNCTION int_to_text_nullzero(int) AS IMPLICIT;

CREATE TABLE o (t text NOT NULL);
CREATE TABLE s (i int NOT NULL);
INSERT INTO o VALUES ('1'), ('5');
INSERT INTO s VALUES (0), (1);

-- how does the parser resolve this?
EXPLAIN (VERBOSE, COSTS OFF) SELECT t FROM o WHERE t NOT IN (SELECT i FROM s);
SELECT t FROM o WHERE t NOT IN (SELECT i FROM s) ORDER BY 1;
-- reference: same predicate evaluated per row with the optimization fenced off
SELECT t, (t NOT IN (SELECT i FROM s OFFSET 0)) AS notin_value FROM o ORDER BY 1;
SELECT t FROM o WHERE t NOT IN (SELECT i FROM s OFFSET 0) ORDER BY 1;
