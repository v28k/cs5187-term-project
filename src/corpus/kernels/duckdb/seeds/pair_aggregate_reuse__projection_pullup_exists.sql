-- composition of rule kernels aggregate_reuse x projection_pullup (duckdb), template exists
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
SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT TRUE AS c0, [1, 2, 3]::int[] AS c1, ((CASE WHEN REGEXP_MATCHES (((a1.c5 || a1.c5) || a1.c5), '[0-9]{2}') THEN 0.0::numeric ELSE CASE WHEN (FALSE OR CASE WHEN TRUE THEN TRUE ELSE FALSE END) THEN 2.25::numeric ELSE (SELECT MIN (0.0::numeric) FROM rc AS a2) END END % 100) * ((a1.c0)::numeric % 100)) AS c2, LEAST (LEAST (1.5::numeric, (SELECT MAX (100.0::numeric) FROM v0 AS a3 WHERE a1.c1)), NULL::numeric) AS c3 FROM t3 AS a1 WHERE FALSE) AS ka WHERE EXISTS (SELECT 1 FROM (SELECT sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) IS NULL) GROUP BY d.label) AS kb);
-- pgfuzz:check kernel:exists SELECT CASE WHEN (SELECT count(*) FROM (SELECT sum(f.v) FROM reuse_owner o JOIN reuse_dim d ON o.dim_id = d.id JOIN reuse_fact f USING (k) WHERE o.k IN (SELECT k FROM reuse_fact GROUP BY k HAVING sum(v) IS NULL) GROUP BY d.label) AS kb) > 0 THEN (SELECT count(*) FROM (WITH RECURSIVE rc(c0) AS (SELECT 1 UNION ALL SELECT r.c0 + 1 FROM rc AS r WHERE r.c0 < 5) SELECT TRUE AS c0, [1, 2, 3]::int[] AS c1, ((CASE WHEN REGEXP_MATCHES (((a1.c5 || a1.c5) || a1.c5), '[0-9]{2}') THEN 0.0::numeric ELSE CASE WHEN (FALSE OR CASE WHEN TRUE THEN TRUE ELSE FALSE END) THEN 2.25::numeric ELSE (SELECT MIN (0.0::numeric) FROM rc AS a2) END END % 100) * ((a1.c0)::numeric % 100)) AS c2, LEAST (LEAST (1.5::numeric, (SELECT MAX (100.0::numeric) FROM v0 AS a3 WHERE a1.c1)), NULL::numeric) AS c3 FROM t3 AS a1 WHERE FALSE) AS ka) ELSE 0 END
