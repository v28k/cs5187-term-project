-- composition of rule kernels aggregate_reuse x common_subexpressions (duckdb), template exists
CREATE TABLE reuse_dim(id INTEGER, label VARCHAR);
INSERT INTO reuse_dim VALUES (10, 'x'), (20, 'b'), (30, 'x'), (40, 'd');
CREATE TABLE reuse_owner(k INTEGER, dim_id INTEGER);
INSERT INTO reuse_owner VALUES (1, 10), (2, 20), (3, 30), (4, 40);
CREATE TABLE reuse_fact(k INTEGER, v INTEGER, w INTEGER);
INSERT INTO reuse_fact VALUES (1, 10, 1), (1, 20, 2), (2, 5, 3), (3, 40, 4), (3, 50, 5), (4, NULL, 6);
PRAGMA explain_output = 'physical_only';
SET disabled_optimizers = 'aggregate_reuse';
EXPLAIN SELECT o.k, d.label, sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) > 25) GROUP BY o.k, d.label;
RESET disabled_optimizers;
EXPLAIN SELECT o.k, d.label, sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) > 25) GROUP BY o.k, d.label;
EXPLAIN SELECT o.k, d.label, sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) > 25) GROUP BY o.k, d.label;
EXPLAIN SELECT o.k, d.label, sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) > 25) GROUP BY o.k, d.label;
SET debug_verify_serializer = true;
SELECT count(*) FROM (SELECT sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) IS NULL) GROUP BY d.label) AS ka WHERE EXISTS (SELECT 1 FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT LIST_HAS_ALL (ARRAY[a1.c0], CASE WHEN TRUE THEN ARRAY_REVERSE (ARRAY[a1.c0]) ELSE ARRAY[1, 2, 3] END) AS c0, 'ß'::text AS c1 FROM t1 AS a1) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT LIST_HAS_ALL (ARRAY[a1.c0], CASE WHEN TRUE THEN ARRAY_REVERSE (ARRAY[a1.c0]) ELSE ARRAY[1, 2, 3] END) AS c0, 'ß'::text AS c1 FROM t1 AS a1) AS kb) > 0 THEN (SELECT count(*) FROM (SELECT sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) IS NULL) GROUP BY d.label) AS ka) ELSE 0 END
