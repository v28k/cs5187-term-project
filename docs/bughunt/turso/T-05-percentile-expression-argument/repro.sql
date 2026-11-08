CREATE TABLE t (a INTEGER, b TEXT);
INSERT INTO t VALUES (1, 'x'), (2, 'y');
SELECT percentile_disc(a + 0, 1) FROM t;     -- Turso: error "Percentile value must be between 0.0 and 1.0 inclusive"; SQLite: 2.0
SELECT percentile_disc(length(b), 1) FROM t; -- Turso: NULL;  SQLite: 1.0
SELECT percentile_cont('5' + 0, 0.5);        -- Turso: NULL;  SQLite: 5.0
SELECT percentile_disc(abs(''), 1);          -- Turso: NULL;  SQLite: 0.0
SELECT percentile_disc(a, 1) FROM t;         -- both 2.0 (a bare column works)
