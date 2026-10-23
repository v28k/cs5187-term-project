-- Shared database state for every fuzzing configuration. Run once per server
-- connection by the executor (setup_sql); test cases run in savepoints on top
-- of it and are rolled back, so every test case sees exactly this state.
-- corpus/schema.yaml describes the same tables for the grammar generator; keep
-- the two in sync.
DROP VIEW IF EXISTS v0 CASCADE;
DROP TABLE IF EXISTS t0, t1, t2, t3, t4, tp, tl, ti CASCADE;

CREATE TABLE t0 (c0 int, c1 text, c2 float8);
CREATE TABLE t1 (c0 int PRIMARY KEY, c1 int REFERENCES t1 (c0) ON DELETE SET NULL ON UPDATE CASCADE, c2 jsonb, c3 int4range);
CREATE TABLE t2 (c0 bigint GENERATED ALWAYS AS IDENTITY, c1 numeric(10, 2) CHECK (c1 >= 0), c2 timestamptz DEFAULT '2024-06-01 00:00:00+00', c3 text[]);
CREATE TABLE t3 (c0 int NOT NULL, c1 bool, c2 date, c3 interval, c4 int[], c5 text COLLATE "C");
CREATE TABLE t4 (c0 int, c1 int GENERATED ALWAYS AS (c0 * 2) VIRTUAL, c2 text GENERATED ALWAYS AS (c0::text || 'x') STORED, c3 numeric);
CREATE TABLE tp (c0 int, c1 text) PARTITION BY RANGE (c0);
CREATE TABLE tp_low PARTITION OF tp FOR VALUES FROM (MINVALUE) TO (100);
CREATE TABLE tp_high PARTITION OF tp FOR VALUES FROM (100) TO (MAXVALUE);
CREATE TABLE tp_def PARTITION OF tp DEFAULT;
CREATE TABLE tl (c0 int, c1 text) PARTITION BY LIST (c1);
CREATE TABLE tl_ab PARTITION OF tl FOR VALUES IN ('a', 'b');
CREATE TABLE tl_null PARTITION OF tl FOR VALUES IN (NULL);
CREATE TABLE tl_def PARTITION OF tl DEFAULT;
CREATE TABLE ti (c0 int, c1 text);
CREATE TABLE ti_child (c2 int) INHERITS (ti);

INSERT INTO t0 SELECT g % 17, md5(g::text), g / 3.0 FROM generate_series(1, 200) AS g;
INSERT INTO t0 VALUES (NULL, NULL, NULL), (0, '', 0.0), (-1, 'x', -1.5);
INSERT INTO t1 (c0, c1, c2, c3) SELECT g, NULLIF(g - 1, 0), jsonb_build_object('k', g, 'a', jsonb_build_array(g, g * 2)), int4range(g, g + 10) FROM generate_series(1, 50) AS g;
INSERT INTO t2 (c1, c2, c3) SELECT g * 1.5, '2024-01-01 00:00:00+00'::timestamptz + g * interval '5 hours', ARRAY[g::text, 'a'] FROM generate_series(1, 30) AS g;
INSERT INTO t3 SELECT g % 23, CASE WHEN g % 5 = 0 THEN NULL ELSE g % 2 = 0 END, '2024-01-01'::date + g,
                      g * interval '7 hours', ARRAY[g, g % 4, NULL], chr(65 + g % 26) FROM generate_series(1, 100) AS g;
INSERT INTO t4 (c0, c3) SELECT CASE WHEN g % 9 = 0 THEN NULL ELSE g % 31 END, g / 7.0 FROM generate_series(1, 120) AS g;
INSERT INTO tp SELECT g, g::text FROM generate_series(1, 200) AS g;
INSERT INTO tl SELECT g, (ARRAY['a', 'b', 'c', NULL])[1 + g % 4] FROM generate_series(1, 80) AS g;
INSERT INTO ti SELECT g, g::text FROM generate_series(1, 20) AS g;
INSERT INTO ti_child SELECT g, g::text, g * 10 FROM generate_series(15, 40) AS g;

CREATE INDEX i0 ON t0 (c0);
CREATE INDEX i1 ON t0 (lower(c1)) WHERE c0 > 5;
CREATE INDEX i2 ON t1 USING gin (c2);
CREATE INDEX i3 ON t1 USING gist (c3);
CREATE INDEX i4 ON t3 (c0, c2);
CREATE INDEX i5 ON t3 USING gin (c4);
CREATE INDEX i6 ON t4 (c2);
CREATE INDEX i7 ON tp (c0);
CREATE INDEX i8 ON t2 USING brin (c1);
CREATE VIEW v0 AS SELECT c0, count(*) AS n FROM t0 GROUP BY c0;
ANALYZE;
