# DF-01: UPDATE / DELETE fail with "No field named __common_expr_1" when SET or WHERE repeats an expression

| | |
|---|---|
| Status | **filed** 8 Nov 2026: issue [#27235](https://github.com/apache/datafusion/issues/27235), PR [#27236](https://github.com/apache/datafusion/pull/27236) (validated by a contributor) |
| Target | Apache DataFusion (https://github.com/apache/datafusion) |
| Kind | valid UPDATE / DELETE rejected with an internal schema error (an optimizer artefact leaks into DML planning) |
| Affected | **`main` bc86321 (8 Nov 2026, 57.0.0-dev), `datafusion-cli` built from source**; datafusion-python 55.0.0 |
| Fix | `fix.patch` (written and tested here) |
| Found by | grammar fuzzer, DataFusion target, internal-error oracle (8 Nov 2026) |

## Reproducer

```sql
CREATE TABLE t (c0 INT, c1 VARCHAR);
INSERT INTO t VALUES (1, 'a'), (NULL, 'b');
UPDATE t SET c0 = COALESCE(c0, 0);
```

Actual: `UPDATE operation on table 't' caused by Schema error: No field named __common_expr_1. Valid fields are c0, c1.`
Expected: 2 rows updated (`(1, 'a')`, `(0, 'b')`).

Found while re-checking on `main`: the WHERE clause is affected too. `UPDATE t SET c1 = 'z' WHERE COALESCE(c0, 0) > 0
AND COALESCE(c0, 0) < 5` and the same `DELETE` fail with `No field named __common_expr_5` (`variants.sql`).

## Root cause

`datafusion/core/src/physical_planner.rs`. For a `MemTable` (`DefaultTableSource`) target, UPDATE and DELETE are not
executed by an operator tree: the planner extracts the assignments (`extract_update_assignments`, from the top
`Projection` of the DML input) and the filters (`extract_dml_filters`, from `Filter` nodes and scan filters), strips
column qualifiers and passes them to `TableProvider::update` / `delete`, which evaluate them against the table's schema.

The DML input has been optimized first. When an expression occurs twice (here the coerced `CAST(c0 AS Int64)` that
`COALESCE(c0, 0)` produces twice), `common_sub_expression_eliminate` computes it once in a new `Projection` below
the assignment projection (or below the filter) and rewrites the uses to the column `__common_expr_N`. The extracted
assignment / predicate then references a column that only exists in the plan, not in the table.

## Fix (`fix.patch`)

`inline_projected_columns(expr, input)` walks down the DML input (through `Projection`, `Filter`, `Sort`, `Limit`)
and replaces each reference to a column produced by a projection with that projection's (unaliased) expression.
`extract_update_assignments` applies it to every assignment and `extract_dml_filters` to every predicate of a `Filter`,
before the qualifiers are stripped. Plans without such projections are unchanged.

## Tests run (8 Nov 2026, `--profile ci`, `main` bc86321 + patch)

- new cases in `dml_update.slt` (3 statements + final check) and `dml_delete.slt` (1 statement + final check): fail on
  `main` (4 + 2 errors, "No field named __common_expr_1/5") and pass with the patch.
- `cargo test --profile ci -p datafusion-sqllogictest --test sqllogictests` (**all 546 test files**, run with both
  DataFusion fixes applied): pass. On the DF-01 branch alone: `dml_update`, `dml_delete`, `update`, `delete` pass.
- `cargo clippy --profile ci -p datafusion --all-targets -- -D warnings`: clean; `cargo fmt --all`: clean.
- Not run here: the extended `cargo test --workspace` command from AGENTS.md (too large for this machine's disk);
  CI runs it.

## Duplicate search (8 Nov 2026)

GitHub search API, apache/datafusion: `UPDATE common_expr is:issue|is:pull-request` → only PRs #10939, #10868 (CSE
alias names, 2024); `UPDATE coalesce created:>2026-05-01` → nothing related. Web search for
`datafusion UPDATE "__common_expr" "No field named"` → PR #16066 (a CSE schema error in aggregates, different path).
`git log` of `main` to bc86321: no change to `extract_update_assignments` / `extract_dml_filters` for this.

## Files

`issue.md` (bug report form fields), `pr.md` (PR template sections), `fix.patch`, `tests.slt.diff` (the test part of
the patch), `repro.sql`, `variants.sql`.
