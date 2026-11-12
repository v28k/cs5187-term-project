-- composition of rule kernels aggregate_function_rewriter x aggregate_reuse (duckdb), template graft_exists
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
SELECT (NULLIF (((LIST_SUM (LIST (35 ORDER BY 35)))::int % NULLIF (500, 0)), (-42)) + (-10)) AS c0 FROM (SELECT * FROM t2 WHERE EXISTS (SELECT 1 FROM (SELECT sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) > 25) GROUP BY d.label) AS kb) OR NOT EXISTS (SELECT 1 FROM (SELECT sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) > 25) GROUP BY d.label) AS kb)) AS a1 GROUP BY GROUPING SETS ((a1.c1), (a1.c2), ());
-- pgfuzz:check kernel:graft_exists SELECT (NULLIF (((LIST_SUM (LIST (35 ORDER BY 35)))::int % NULLIF (500, 0)), (-42)) + (-10)) AS c0 FROM t2 AS a1 GROUP BY GROUPING SETS ((a1.c1), (a1.c2), ())
