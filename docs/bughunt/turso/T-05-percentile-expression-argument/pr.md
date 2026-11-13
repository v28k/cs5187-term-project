**Title:** core/translate: read external aggregate arguments into consecutive registers

**Body** (sections of `.github/pull_request_template.md`; tick "allow edits from maintainers" when opening):

## Description

The step of an external aggregate (`AggFunc::External`, e.g. `percentile_disc(Y, P)` / `percentile_cont(Y, P)`)
reads its arguments from consecutive registers starting at `expr_reg`, but `translate_aggregation_step` resolved each
argument with `resolve_expr`, which picks its own register. When the first argument is an expression, its
temporaries end up between the arguments, so the step read a temporary as the fraction.

This adds `AggArgumentSource::translate_all`, which translates all arguments into one block of registers (the same
way `translate_function` does for scalar functions), and uses it for external aggregates.

Closes #ISSUE

## Motivation and context

Wrong results compared with SQLite:

```sql
CREATE TABLE t (a INTEGER, b TEXT);
INSERT INTO t VALUES (1, 'x'), (2, 'y');
SELECT percentile_disc(a + 0, 1) FROM t;      -- was: "Percentile value must be between 0.0 and 1.0 inclusive"; now 2.0
SELECT percentile_disc(length(b), 1) FROM t;  -- was: NULL; now 1.0
```

Tests: `sqlite/conformance/sqlite-sqltests/agg-functions/percentile-expression-argument.sqltest` (5 cases, expected
values checked against SQLite 3.54.1). All 5 fail without the change and pass with it. The full `sqlite-sqltests`
corpus passes with the change (cli backend: 12700 passed, 4 skipped).

## Description of AI Usage

As filed in PR #11595.
