CREATE TABLE t(x INTEGER);
INSERT INTO t VALUES (1), (3);

-- SQLite: 0|1    Turso: Parse error: misuse of aggregate function max()
SELECT max(x) IN (SELECT 1), count(*) OVER () FROM t;

-- SQLite: 0|1    Turso: Parse error: misuse of aggregate function sum()
SELECT sum(x) NOT IN (SELECT 4), row_number() OVER () FROM t;

-- SQLite: 1      Turso: Parse error: misuse of aggregate function max()
SELECT max(x) IN (SELECT 3) FROM t ORDER BY sum(x) OVER ();

-- expected 1|1   Turso: the process panics
--   panicked at core/ext/function.rs:91: internal error: entered unreachable code: aggregate called in scalar context
SELECT median(x) IN (SELECT 2), count(*) OVER () FROM t;
