**Title:** percentile_disc/percentile_cont give NULL or a bogus error when the first argument is an expression

(Turso has no issue template; this is the whole issue body.)

`percentile_disc(Y, P)` and `percentile_cont(Y, P)` work when `Y` is a bare column or a literal, but return NULL or
fail with a "percentile value" error when `Y` is any other expression. SQLite 3.54.1 returns the expected values.

```sql
CREATE TABLE t (a INTEGER, b TEXT);
INSERT INTO t VALUES (1, 'x'), (2, 'y');

SELECT percentile_disc(a, 1) FROM t;          -- 2.0 (OK)
SELECT percentile_disc(a + 0, 1) FROM t;      -- Error: Percentile value must be between 0.0 and 1.0 inclusive  (SQLite: 2.0)
SELECT percentile_disc(length(b), 1) FROM t;  -- NULL  (SQLite: 1.0)
SELECT percentile_cont('5' + 0, 0.5);         -- NULL  (SQLite: 5.0)
SELECT percentile_disc(abs(''), 1);           -- NULL  (SQLite: 0.0)
```

Cause: for an external aggregate, `translate_aggregation_step` (`core/translate/aggregation.rs`) resolves each
argument with `resolve_expr`, which picks its own register, but `AggStep` then reads argument `i` from
`expr_reg + i`. When `Y` is an expression, its temporaries are allocated between the two arguments, so the step reads
a temporary as `P`. A fix is in the linked PR.

Unrelated to this and not changed by the fix: `SELECT percentile_disc('5', 1)` returns 5.0, where SQLite raises
"input to percentile_disc() is not numeric".

Version: `main` at 9b71df9ab (tursodb built from source, Linux x86_64); also pyturso 0.8.3.
Found with a grammar-based SQL fuzzer comparing Turso with SQLite.
