-- Schema of the DuckDB target: the PostgreSQL corpus schema without partitions,
-- inheritance, range types and row-level security, which DuckDB does not have.
-- jsonb is an alias of DuckDB's JSON type so the grammar's PostgreSQL type names work.
CREATE TYPE jsonb AS JSON;
CREATE TABLE t0 (c0 int, c1 text, c2 float8);
CREATE TABLE t1 (c0 int PRIMARY KEY, c1 int, c2 jsonb);
CREATE TABLE t2 (c0 bigint, c1 numeric(10, 2) CHECK (c1 >= 0), c2 timestamptz DEFAULT '2024-06-01 00:00:00+00', c3 text[]);
CREATE TABLE t3 (c0 int NOT NULL, c1 bool, c2 date, c3 interval, c4 int[], c5 text);
CREATE TABLE t4 (c0 int, c1 int GENERATED ALWAYS AS (c0 * 2) VIRTUAL, c3 numeric(18, 3));
CREATE TABLE tp (c0 int NOT NULL, c1 text);
CREATE TABLE tl (c0 int, c1 text);
CREATE TABLE ti (c0 int, c1 text);
INSERT INTO t0 SELECT g % 17, md5(g::text), g / 3.0 FROM generate_series(1, 200) AS s(g);
INSERT INTO t0 VALUES (NULL, NULL, NULL), (0, '', 0.0), (-1, 'x', -1.5);
INSERT INTO t1 SELECT g, NULLIF(g - 1, 0), json_object('k', g, 'a', json_array(g, g * 2)) FROM generate_series(1, 50) AS s(g);
INSERT INTO t2 SELECT g, g * 1.5, '2024-01-01 00:00:00+00'::timestamptz + g * interval '5 hours', [g::text, 'a'] FROM generate_series(1, 30) AS s(g);
INSERT INTO t3 SELECT g % 23, CASE WHEN g % 5 = 0 THEN NULL ELSE g % 2 = 0 END, '2024-01-01'::date + g::int,
                      g * interval '7 hours', [g::int, (g % 4)::int, NULL], chr((65 + g % 26)::int) FROM generate_series(1, 100) AS s(g);
INSERT INTO t4 (c0, c3) SELECT CASE WHEN g % 9 = 0 THEN NULL ELSE g % 31 END, g / 7.0 FROM generate_series(1, 120) AS s(g);
INSERT INTO tp SELECT g, g::text FROM generate_series(1, 200) AS s(g);
INSERT INTO tl SELECT g, (['a', 'b', 'c', NULL])[1 + g % 4] FROM generate_series(1, 80) AS s(g);
INSERT INTO ti SELECT g, g::text FROM generate_series(1, 40) AS s(g);
CREATE VIEW v0 AS SELECT c0, count(*) AS n FROM t0 GROUP BY c0;
CREATE INDEX i0 ON t0 (c0);
CREATE INDEX i4 ON t3 (c0, c2);
