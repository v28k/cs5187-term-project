# D-01: min/max over a nested value that contains a subquery fails with "Cannot copy BoundSubqueryExpression"

| | |
|---|---|
| Status | **ready to file** (not filed) |
| Target | DuckDB (https://github.com/duckdb/duckdb) |
| Kind | valid query rejected with an internal-style error; **regression in 2.0.0** for LIST/STRUCT/ARRAY arguments |
| Severity | medium: any `min`/`max`/`min(x, n)`/`max(x, n)` whose argument is a nested value computed with a subquery (scalar subquery, correlated subquery, `EXISTS` inside `CASE`) fails |
| Affected | 2.0.0, nightly 2.1.0.dev2610310630 (python wheel). Works in 1.5.6, 1.4.4, 1.3.2. The same error for a VARCHAR argument under a collation (`SET default_collation = 'nocase'`) is older: 1.5.6 fails too |
| Introduced by | 2ef9f76b2e "Apply collations to nested values in min/max aggregates" (1 Oct 2026); the `min(x, n)` path got the same pattern in 5432471e7a (6 Oct 2026) |
| Found by | our grammar fuzzer (Arbor/pgfuzz, DuckDB target), internal-error oracle; 6 candidates in 600 generated test cases (seed 2) |

## Minimal reproducer

```sql
CREATE TABLE a (x INTEGER);
INSERT INTO a VALUES (1), (2);
SELECT min((SELECT [1])) FROM a;
```

Actual (2.0.0, nightly):

```
Serialization Error: Cannot copy BoundSubqueryExpression
```

Expected: `[1]` (what 1.5.6 returns). More variants, all failing the same way, are in `repro.sql`:
`max((SELECT {'k': x}))` (correlated), `max((SELECT [x]), 1)` (the N variant),
`min(CASE WHEN EXISTS (SELECT 1) THEN [x] END)`. A scalar argument (`min((SELECT 'x'))`) works unless a collation applies.

Why the expected result is right: the subquery returns one value per row; `min`/`max` of those values is
well defined, other DuckDB releases return it, and `arg_min((SELECT [1]), 1)` / `first((SELECT [1]))` work on 2.0.0.

## Root cause

`src/function/aggregate/distributive/minmax.cpp`, `BindMinMax` (and `MinMaxNBind` for the N variant):

```cpp
const auto collation = MinMaxUsesCollation(context, input_type);
auto collated_arg = collation ? arguments[0]->Copy() : nullptr;
```

Since 2ef9f76b2e, `MinMaxUsesCollation` returns true for every STRUCT, LIST and ARRAY argument
(`nested_collation`), so the binder copies the argument expression to build the collated sort key.
`BoundSubqueryExpression::Copy()` throws (`src/planner/expression/bound_subquery_expression.cpp:22`), so any
nested argument that contains a subquery now fails at bind time. Before 2.0.0 this path was only taken for
collated VARCHAR, BIT, TIME_TZ and VARIANT, which is why `SET default_collation='nocase'; SELECT min((SELECT 'B')) FROM a;`
fails in 1.5.6 as well.

Disabling the optimizer does not help (`PRAGMA disable_optimizer`): the failure is in binding.

Possible fixes (for the maintainers to choose; not implemented or tested here):
1. when the argument contains a subquery, avoid the copy: e.g. take the non-collated path when no collation
   actually applies to the nested type (the common case), which restores the 1.5 behaviour;
2. or project the argument once (so both the value and the collated key reference the projected column),
   which also fixes the older collated-VARCHAR case;
3. at minimum raise a clear binder error, as was done for similar cases (PR #27180, PR #26977).

## Duplicate search (7 Nov 2026)

- DuckDB issues/PRs mentioning "Cannot copy BoundSubqueryExpression": #15496 (`unnest((SELECT row(1)))`), #13943
  (`unnest` of a struct subquery), #2749 (subquery in an IN list), #7128 (fuzzer collection, JOIN ON), PRs #27180
  (`switch()` key), #26977 (COPY ORDER BY), #26043 (window DEFINE). None covers min/max; none mentions the 2.0
  regression.
- `git log` of duckdb main up to d4eea3f208 (6 Nov 2026): no fix for minmax.cpp after 2ef9f76b2e / 5432471e7a.
- Owner: please re-check https://github.com/duckdb/duckdb/issues?q=min+max+subquery+copy before filing.

## How the fuzzer found it

Config `src/configs/duckdb.yaml` (grammar `postgres.pgg` + overlay `overlays/duckdb.pgg`), `pgfuzz sample -n 600
--execute --seed 2`. The generated query had `MIN((SELECT MAX(ARRAY['x', NULL]) FROM t0))` in a scalar
subquery; the token reducer reduced it to `SELECT MIN((SELECT [])) FROM (t1 JOIN tp ON NULL)`, then by hand to the
reproducer above. The DuckDB driver classifies "Cannot copy Bound…" serialization errors as internal errors.
Known-bug entry: `src/known_bugs/duckdb.yaml` (`duckdb-D01`).

## Files

- `issue.md`: issue text for https://github.com/duckdb/duckdb/issues/new (bug report form)
- `repro.sql`: all variants
- `minmax_subquery_argument.test`: sqllogictest for `test/sql/aggregate/aggregates/` (for a fix PR)
- `steps.md`: what to do
