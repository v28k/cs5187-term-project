-- E-02: "plan should not reference subplan's variable" on master since f8da64e6
-- (2 Nov 2026). Self-contained, default settings; run with psql -X -f <file>.
DROP TABLE IF EXISTS d_a, d_b;
CREATE TABLE d_a (x int NOT NULL);
CREATE TABLE d_b (x int, pad text);
INSERT INTO d_a SELECT g % 10 FROM generate_series(1, 1000) g;
INSERT INTO d_b SELECT g, repeat('x', 100) FROM generate_series(1, 100000) g;
CREATE INDEX ON d_b (x);
VACUUM ANALYZE d_a, d_b;
-- ERROR:  plan should not reference subplan's variable
SELECT count(*) FROM d_a a JOIN d_b b ON a.x = b.x WHERE 5 > ALL (SELECT b.x);
-- with the Memoize node disabled the same query returns 400
SET enable_memoize = off;
SELECT count(*) FROM d_a a JOIN d_b b ON a.x = b.x WHERE 5 > ALL (SELECT b.x);
