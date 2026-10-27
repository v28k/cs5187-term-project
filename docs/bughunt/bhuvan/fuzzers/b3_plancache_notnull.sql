-- H-B3: cached plans that relied on NOT NULL constraints must be invalidated
\pset null '<NULL>'
CREATE TABLE o (x int NOT NULL);
CREATE TABLE s (y int NOT NULL);
INSERT INTO o VALUES (1), (2);
INSERT INTO s VALUES (1);
SET plan_cache_mode = force_generic_plan;
PREPARE q AS SELECT x FROM o WHERE x NOT IN (SELECT y FROM s) ORDER BY x;
EXPLAIN (COSTS OFF) EXECUTE q;
EXECUTE q;                                   -- 2
ALTER TABLE s ALTER COLUMN y DROP NOT NULL;
INSERT INTO s VALUES (NULL);
EXPLAIN (COSTS OFF) EXECUTE q;               -- must no longer be an anti join
EXECUTE q;                                   -- expected: 0 rows
-- inheritance: parent had no children at plan time, a child holding NULLs appears later
CREATE TABLE p (y int NOT NULL NO INHERIT);
INSERT INTO p VALUES (1);
PREPARE q2 AS SELECT x FROM o WHERE x NOT IN (SELECT y FROM p) ORDER BY x;
EXPLAIN (COSTS OFF) EXECUTE q2;
EXECUTE q2;                                  -- 2
CREATE TABLE pc () INHERITS (p);
ALTER TABLE pc ALTER COLUMN y DROP NOT NULL;
INSERT INTO pc VALUES (NULL);
EXPLAIN (COSTS OFF) EXECUTE q2;
EXECUTE q2;                                  -- expected: 0 rows
-- SQL function body cached plan (SQL functions are planned per call; checked anyway)
CREATE FUNCTION f() RETURNS SETOF int LANGUAGE sql STABLE AS $$ SELECT x FROM o WHERE x NOT IN (SELECT y FROM p) $$;
SELECT * FROM f();                           -- expected: 0 rows
-- plpgsql cached plan
CREATE TABLE s2 (y int NOT NULL);
INSERT INTO s2 VALUES (1);
CREATE FUNCTION g() RETURNS bigint LANGUAGE plpgsql AS $$ BEGIN RETURN (SELECT count(*) FROM o WHERE x NOT IN (SELECT y FROM s2)); END $$;
SELECT g();                                  -- 1
ALTER TABLE s2 ALTER COLUMN y DROP NOT NULL;
INSERT INTO s2 VALUES (NULL);
SELECT g();                                  -- expected: 0
