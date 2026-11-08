# T-05: percentile_disc / percentile_cont with an expression as the value argument

| | |
|---|---|
| Status | **ready to file: issue + fix PR** (not filed) |
| Target | Turso (https://github.com/tursodatabase/turso) |
| Kind | wrong result (NULL instead of a value) and a bogus error; differential oracle Turso vs SQLite 3.54.1 |
| Affected | pyturso 0.8.3; **`main` 9b71df9ab (7 Nov 2026), `tursodb` built from source on 8 Nov 2026** |
| Fix | `fix.patch` (written and tested here) |
| Found by | Turso campaign (8 Nov 2026), cross-engine differential; cluster of candidates reduced to `SELECT PERCENTILE_DISC(ABS(''), 1)` etc. |

## Reproducer and expected results

```sql
CREATE TABLE t (a INTEGER, b TEXT);
INSERT INTO t VALUES (1, 'x'), (2, 'y');
SELECT percentile_disc(a + 0, 1) FROM t;     -- Turso main: error "Percentile value must be between 0.0 and 1.0 inclusive"; SQLite: 2.0
SELECT percentile_disc(length(b), 1) FROM t; -- Turso main: NULL;  SQLite: 1.0
SELECT percentile_cont('5' + 0, 0.5);        -- Turso main: NULL;  SQLite: 5.0
SELECT percentile_disc(abs(''), 1);          -- Turso main: NULL;  SQLite: 0.0
SELECT percentile_disc(a, 1) FROM t;         -- both 2.0 (a bare column works)
```

Expected values: SQLite 3.54.1 (APSW), whose percentile extension Turso's `percentile_disc(Y, P)` /
`percentile_cont(Y, P)` follow. The two-argument (non-`WITHIN GROUP`) form is the external aggregate from
`core/percentile.rs`.

## Root cause

`core/translate/aggregation.rs`, `translate_aggregation_step`, branch `AggFunc::External`:

```rust
let expr_reg = agg_arg_source.translate(program, referenced_tables, resolver, 0)?;
for i in 0..argc {
    if i != 0 {
        let _ = agg_arg_source.translate(program, referenced_tables, resolver, i)?;
    }
    ...
}
program.emit_insn(Insn::AggStep { col: expr_reg, ... })   // reads args from expr_reg .. expr_reg + argc - 1
```

`translate` calls `resolve_expr`, whose documentation says callers must use the returned register and cannot assume a
destination. For a bare column the two arguments happen to land in consecutive registers; for an expression such as
`a + 0` the temporaries of the first argument are allocated between them, so `AggStep` reads a temporary as the
fraction (`a + 0`'s operand: 1 → "must be between 0.0 and 1.0" for row 2, or a NULL → NULL result).

## Fix (`fix.patch`)

New `AggArgumentSource::translate_all`: for expression arguments it allocates one block of `argc` registers and
translates argument `i` into `start + i` with `translate_expr` (the idiom of `translate_function` for scalar
functions); for register-sourced arguments (already consecutive) it returns the start register. The external-aggregate
branch uses it. `cargo fmt -p turso_core` clean.

## Tests run (8 Nov 2026, debug `tursodb` of 9b71df9ab + patch)

- new `sqlite/conformance/sqlite-sqltests/agg-functions/percentile-expression-argument.sqltest` (5 tests, expected
  values from SQLite 3.54.1): 5 pass with the patch, **5 fail without it**.
- existing `agg-functions/percentile-fraction.sqltest`: 5 pass.
- full `sqlite-sqltests` corpus, cli backend, with the patch: **12700 passed, 4 skipped, 0 failed** (542 s).

## Duplicate search (8 Nov 2026)

GitHub search API, tursodatabase/turso: `percentile is:issue` → #10413 (out-of-range P returns NULL instead of an
error), #11435 (fraction using a GROUP BY column), #11385, #11395, #11424 (tursopg panics), #1060, #1240 — none about
an expression as the value argument. `percentile is:pull-request` → #10435, #11434, #10373, #8586 — none touches
argument registers. `git log` of `main` to 9b71df9ab: no change to the External branch of
`translate_aggregation_step` since the bug.

## Files

`issue.md` (issue body; Turso has no issue template), `pr.md` (PR title and body in Turso's PR template),
`fix.patch`, `percentile-expression-argument.sqltest` (the test in the patch), `repro.sql`, `steps.md`.

## Follow-up after review (8 Nov 2026)

The PR (tursodatabase/turso#11595, head 79d092a) got one review finding: SQLite's percentile aggregates reject a
non-NULL TEXT or BLOB value ("input to <name>() is not numeric"), Turso read numeric-looking text as a number. Fixed
in one more commit, "core: reject non-numeric input to percentile aggregates" (`followup-nonnumeric.patch`), with 5
more sqltest cases; the full sqlite-sqltests corpus (12707 passed), `cargo fmt --check` and clippy pass. Details:
`followup-review.md`.
