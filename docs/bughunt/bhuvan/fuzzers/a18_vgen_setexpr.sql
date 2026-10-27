-- H-A18: NOT NULL on a virtual generated column vs ALTER ... SET EXPRESSION
\pset null '<NULL>'
CREATE TABLE v (a int, g int GENERATED ALWAYS AS (a) VIRTUAL NOT NULL);
INSERT INTO v VALUES (1), (2);
-- new expression yields NULL for a = 1: must be rejected (or constraint re-checked)
ALTER TABLE v ALTER COLUMN g SET EXPRESSION AS (NULLIF(a, 1));
SELECT a, g, g IS NULL AS isnull FROM v ORDER BY a;
SELECT count(*) FROM v WHERE g IS NULL;
-- variant: drop the expression's NOT NULL source through ALTER TYPE of the base column
CREATE TABLE v2 (a text, g int GENERATED ALWAYS AS (length(a)) VIRTUAL NOT NULL);
INSERT INTO v2 VALUES ('x');
ALTER TABLE v2 ALTER COLUMN a TYPE int USING NULL;   -- a becomes NULL, length(NULL) is NULL
SELECT a, g FROM v2;
SELECT count(*) FROM v2 WHERE g IS NULL;
-- NOT IN path that trusts NOT NULL via catalog
CREATE TABLE o (x int NOT NULL);
INSERT INTO o VALUES (5);
SELECT * FROM o WHERE x NOT IN (SELECT g FROM v);
