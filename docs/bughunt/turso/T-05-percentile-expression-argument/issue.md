**Title:** percentile_disc/percentile_cont give NULL or a bogus error when the first argument is an expression

`percentile_disc` and `percentile_cont` work when the first argument is a bare column or a literal, but return NULL
(or fail with a "percentile value" error) when it is any other expression. SQLite 3.54.1 returns the expected values.

```sql
CREATE TABLE t (a INTEGER, b TEXT);
INSERT INTO t VALUES (1, 'x'), (2, 'y');

SELECT percentile_disc(a, 1) FROM t;          -- 2.0 (OK)
SELECT percentile_disc(a + 0, 1) FROM t;      -- Error: Percentile value must be between 0.0 and 1.0 inclusive  (SQLite: 2.0)
SELECT percentile_disc(length(b), 1) FROM t;  -- NULL  (SQLite: 1.0)
SELECT percentile_cont('5' + 0, 0.5);         -- NULL  (SQLite: 5.0)
SELECT percentile_disc(abs(''), 1);           -- NULL  (SQLite: 0.0)
```

The error for `a + 0` suggests the arguments are read from the wrong registers when the value argument has to be
computed. (Related, minor: `SELECT percentile_disc('5', 1)` returns 5.0 where SQLite raises "input to percentile_disc()
is not numeric".)

Version: pyturso 0.8.3 (Python bindings, Linux x86_64). Found with a grammar-based SQL fuzzer comparing Turso with SQLite.
