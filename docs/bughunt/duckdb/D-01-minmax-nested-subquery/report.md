# D-01: min/max over a nested value that contains a subquery fails with "Cannot copy BoundSubqueryExpression"

| | |
|---|---|
| Status | **ready to file: issue + fix PR** (not filed) |
| Target | DuckDB (https://github.com/duckdb/duckdb) |
| Kind | valid query rejected with an internal-style error; **regression in 2.0.0** for LIST/STRUCT/ARRAY arguments |
| Severity | medium: any `min`/`max`/`min(x, n)`/`max(x, n)` whose argument is a nested value computed with a subquery (scalar subquery, correlated subquery, `EXISTS` inside `CASE`) fails |
| Affected | 2.0.0; nightly wheel 2.1.0.dev2610310630 (71f47d410f); **`main` d4eea3f208 (6 Nov 2026, v2.1.0-dev82473, built from source on 8 Nov 2026)**. Works in 1.5.6, 1.4.4, 1.3.2 |
| Introduced by | 2ef9f76b2e "Apply collations to nested values in min/max aggregates" (1 Oct 2026); the `min(x, n)` path got the same pattern in 5432471e7a (6 Oct 2026) |
| Fix | `fix.patch` (written and tested here, see below) |
| Found by | our grammar fuzzer (Arbor/pgfuzz, DuckDB target), internal-error oracle; 6 candidates in 600 generated test cases (seed 2) |

## Minimal reproducer

```sql
CREATE TABLE a (x INTEGER);
INSERT INTO a VALUES (1), (2);
SELECT min((SELECT [1])) FROM a;
```

Actual (2.0.0, nightly, `main` d4eea3f208): `Serialization Error: Cannot copy BoundSubqueryExpression`.
Expected: `[1]` (what 1.5.6 returns). More variants, all failing the same way, are in `repro.sql`:
`max((SELECT {'k': x}))` (correlated), `max((SELECT [x]), 1)` (the N variant),
`min(CASE WHEN EXISTS (SELECT 1) THEN [x] END)`.

Why the expected result is right: the subquery returns one value per row; `min`/`max` of those values is
well defined, other DuckDB releases return it, and `arg_min((SELECT [1]), 1)` / `first((SELECT [1]))` work on 2.0.0.

## Root cause

`src/function/aggregate/distributive/minmax.cpp`, `BindMinMax` (and `MinMaxNBind` for the N variant):

```cpp
const auto collation = MinMaxUsesCollation(context, input_type);
auto collated_arg = collation ? arguments[0]->Copy() : nullptr;
if (collation && ExpressionBinder::PushCollation(context, collated_arg, collated_arg->GetReturnType())) {
```

Since 2ef9f76b2e, `MinMaxUsesCollation` returns true for every STRUCT, LIST and ARRAY argument, so the binder copies
the argument expression *before* knowing whether a collation applies to the nested type at all.
`BoundSubqueryExpression::Copy()` throws (`src/planner/expression/bound_subquery_expression.cpp`), so every nested
argument that contains a subquery fails at bind time, even `LIST(INTEGER)`, where `PushCollation` then returns false
and the copy would have been discarded. Disabling the optimizer does not help: the failure is in binding.

## Fix (`fix.patch`)

A helper `GetCollatedMinMaxArgument` first calls `PushCollation` on a placeholder `BoundReferenceExpression` of the
argument's type; only when a collation applies does it copy the argument and push the collation onto the copy. Both
`BindMinMax` and `MinMaxNBind` use it. Behaviour for collated arguments is unchanged (the same collation functions are
pushed onto the same copy); arguments with no applicable collation are no longer copied, which restores the 1.5
behaviour for nested values.

Not covered (and not a regression): an argument that both needs a collation *and* contains a subquery, e.g.
`SET default_collation = 'nocase'; SELECT min((SELECT 'B')) FROM a;` still fails as in 1.5.6, because the value and
the collated sort key are two separate expressions there. The PR text mentions it as a known limitation.

## Tests run (8 Nov 2026, `make release` of d4eea3f208 + patch, Linux x86_64, gcc 13.3)

- new `test/sql/aggregate/aggregates/test_minmax_subquery_argument.test`: passes with the patch (9 assertions);
  every query in it fails on unpatched `main` with "Cannot copy BoundSubqueryExpression".
- `unittest "test/sql/collate/*"`: all passed (1245 assertions, 43 test cases; includes `collate_struct_minmax.test`
  from 2ef9f76b2e).
- `unittest "test/sql/subquery/*"`: all passed (7976 assertions, 125 test cases).
- `unittest "test/sql/function/list/*"`: all passed (9982 assertions, 137 test cases).
- `unittest "test/sql/aggregate/*"`: 261091 of 261092 assertions passed; the one failure,
  `test_string_agg_overflow.test_slow:10`, fails identically on unpatched `main` (unrelated).
- full fast suite (`unittest` with no arguments) with the patch: **All tests passed** (8751 test cases,
  6719874 assertions, 212 skipped for missing extensions/environment).
- `clang-format` 11.0.1 (the project's version): no changes.

## Duplicate search

- 7 Nov 2026: DuckDB issues/PRs mentioning "Cannot copy BoundSubqueryExpression": #15496 (`unnest((SELECT row(1)))`),
  #13943, #2749, #7128, #5435, #5984, #5788, #2452; PRs #27180 (`switch()` key), #26977 (COPY ORDER BY). None covers
  min/max, none mentions the 2.0 regression.
- 8 Nov 2026 (GitHub search API): `"Cannot copy BoundSubqueryExpression" is:issue` (8 results, none about min/max),
  `is:pull-request` (2, listed above); `min max nested collation created:>2026-09-15` (PRs #28430, #26581: other
  min/max collation work, no fix for this). Web search: no report.
- `git log` of `main` up to d4eea3f208: the last change to `minmax.cpp` is 2635432e30 (fallible N-variants); no fix.

## How the fuzzer found it

Config `src/configs/duckdb.yaml` (grammar `postgres.pgg` + overlay `overlays/duckdb.pgg`), `pgfuzz sample -n 600
--execute --seed 2`. The generated query had `MIN((SELECT MAX(ARRAY['x', NULL]) FROM t0))` in a scalar
subquery; the token reducer reduced it to `SELECT MIN((SELECT [])) FROM (t1 JOIN tp ON NULL)`, then by hand to the
reproducer above. Known-bug entry: `src/known_bugs/duckdb.yaml` (`duckdb-D01`).

## Files

- `issue.md`: issue text (bug report form fields)
- `pr.md`: PR title and description
- `fix.patch`: `git format-patch` of the fix + test against `main` d4eea3f208
- `test_minmax_subquery_argument.test`: the test in the patch
- `repro.sql`: all variants
- `steps.md`: what to do, in order
