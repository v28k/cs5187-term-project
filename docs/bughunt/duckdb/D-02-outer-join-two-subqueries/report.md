# D-02: outer-join / MERGE condition with two subqueries fails with "INTERNAL Error: Failed to bind column reference"

| | |
|---|---|
| Status | **fixed upstream (57a6875edf, PR #28246 "Fix internal error with correlated IN under a mark join", which fixes #28156; merged 2 Nov 2026). Do not file.** |
| Target | DuckDB (https://github.com/duckdb/duckdb) |
| Kind | INTERNAL error on a valid query (internal-error oracle) |
| Severity | medium: LEFT/RIGHT JOIN and MERGE conditions that combine an uncorrelated scalar subquery compared with `ANY` over a list of columns from both sides and a second subquery fail |
| Affected | 2.0.0, nightly 2.1.0.dev2610310630 (71f47d410f, 31 Oct 2026). **Not** `main` d4eea3f208 (6 Nov 2026). In 1.5.6 the same queries raised `Not implemented Error: Cannot perform non-inner join on subquery!`, so this is in the support for subqueries in non-inner join conditions that is new in 2.0 |
| Found by | our grammar fuzzer, DuckDB campaign (nightly vs 2.0.0, 7 Nov 2026), internal-error oracle; signature 0184a1f8f3ea; found on a MERGE statement |

## Minimal reproducer

```sql
CREATE TABLE t (a INTEGER, b BOOLEAN);
CREATE TABLE u (c INTEGER);
INSERT INTO t VALUES (1, true), (6, false);
INSERT INTO u VALUES (1);
SELECT * FROM t LEFT JOIN (SELECT 5 AS x) s ON ((SELECT 1) = ANY ([t.a + s.x]) OR 1 IN (SELECT c FROM u));
```

Actual: `INTERNAL Error: Failed to bind column reference "a" [38.0] (bindings: {#[48.0]})`
(RIGHT JOIN and MERGE: same error for "x"). Expected: `(1, true, 5), (6, false, 5)`.

Why that is the right answer: `(SELECT 1) = ANY([t.a + s.x])` is false for both rows and `1 IN (SELECT c FROM u)` is
true, so every row matches. The same query with the constant `1` instead of `(SELECT 1)`, and the INNER JOIN form,
return exactly these rows on 2.0.0.

What is needed (each removal makes it work): an outer join or MERGE; an uncorrelated scalar subquery compared with
`= ANY(list)` where the list references columns of both join sides; and a second subquery in the same condition.

## Where (not fully root-caused)

`src/planner/binder/query_node/plan_subquery.cpp`, `RecursiveDependentJoinPlanner::PlanJoinSubqueries` /
`PlanJoinExpressions`: each subquery of a non-inner join condition is planned into one side of the join (the
uncorrelated one into the LEFT side). With two subqueries the join side is rewritten twice; afterwards the condition
still refers to the column binding the first rewrite replaced (`Failed to bind column reference "a" [38.0]`, while
the child only exposes `#[48.0]`). We did not build DuckDB to confirm the exact step.

## Duplicate search (7 Nov 2026)

- DuckDB `main` up to d4eea3f208 (6 Nov 2026): related recent fixes 57a6875edf "Fix internal error with correlated IN
  under a mark join", b0320d7a00, d2f0487a96; none covers this pattern (it still fails on the nightly).
- Duplicate search: https://github.com/duckdb/duckdb/issues?q=%22Failed+to+bind+column+reference%22+join+subquery before filing.

## Files

`issue.md`, `repro.sql`, `outer_join_two_subqueries.test` (sqllogictest for `test/sql/subquery/scalar/`), `steps.md`.

## Re-check on `main` (8 Nov 2026): fixed upstream

- `main` d4eea3f208 (v2.1.0-dev82473), built from source: all three statements of `repro.sql` succeed and return the
  expected rows (`(1, true, 5), (6, false, 5)` for the LEFT and the RIGHT JOIN; MERGE inserts nothing).
- The nightly wheel 2.1.0.dev2610310630 (71f47d410f) still fails, also with `PRAGMA disable_optimizer`, so the bug is
  in subquery planning, not in an optimizer rule.
- Fixing commit, confirmed by reverting only its change to `src/planner/subquery/flatten_dependent_join.cpp` on
  d4eea3f208 and rebuilding: all three errors come back (`Failed to bind column reference "a" [38.0]`, `"x" [39.0]`,
  `"x" [34.0]`). The commit is 57a6875edf "Fix internal error with correlated IN under a mark join (#28246)", fixing
  #28156: decorrelation added the correlated column to a MARK join's left input (here the mark join of
  `1 IN (SELECT c FROM u)` above the lateral join that the pair-dependent rewrite builds for the outer join with the
  correlated `ANY`) but not to its `left_projection_map`.
- Related open issue, still failing on `main`: #27719 (`LEFT JOIN ... ON false AND r.a IN (SELECT 3) WHERE true`,
  same error text, different path). Not ours to report.

Nothing to file. Optional: `outer_join_two_subqueries.test` covers a different shape (outer join + `= ANY(list)` over
both sides + a second subquery) than the test added by #28246; it passes on `main` and could be offered as extra
regression coverage, but that is low value and not prepared as a PR.
