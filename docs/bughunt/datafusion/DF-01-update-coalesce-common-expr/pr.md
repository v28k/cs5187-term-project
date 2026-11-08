**Title:** fix: inline common subexpressions in UPDATE assignments and DML filters

**Body** (sections of `.github/pull_request_template.md`):

## Which issue does this PR close?

- Closes #ISSUE.

## Rationale for this change

`UPDATE` and `DELETE` fail with `Schema error: No field named __common_expr_1` when the SET expressions or the WHERE
clause repeat an expression, e.g. `UPDATE t SET c0 = COALESCE(c0, 0)` on an INT column (the column is cast to BIGINT
twice). Common subexpression elimination moves the repeated expression into a projection below, but the assignments
and filters handed to the table provider must only reference the table's own columns.

## What changes are included in this PR?

In `physical_planner.rs`, a new helper `inline_projected_columns` walks down the DML input (through projections,
filters, sorts and limits) and replaces references to projected columns with the expressions that compute them.
`extract_update_assignments` applies it to every assignment and `extract_dml_filters` to every predicate of a
`Filter`, before the qualifiers are stripped and the expressions reach the provider.

## What is the testing strategy for this PR?

New cases in `dml_update.slt` (repeated expression in SET, in SET with a WHERE, and in WHERE) and `dml_delete.slt`
(repeated expression in WHERE). They fail on `main` with the schema error above and pass with this change. The whole
sqllogictest suite passes locally (`cargo test --profile ci -p datafusion-sqllogictest --test sqllogictests`).

## Are there any user-facing changes?

No API changes; these statements now run instead of failing.
