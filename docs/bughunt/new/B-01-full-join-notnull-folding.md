# B-01: FULL JOIN that works on 18 fails on 19/master: NOT NULL-based folding removes the only hashable join clause

Status: **confirmed (3/3 fresh databases), root-caused, patch written, `make check` passes (239/239). NOT FILED.**
Confidence: **medium-high** that it is a real regression; medium that upstream fixes it this way
(they may prefer a different fix, see "Fix" below).
Found 23 Oct 2026 by hunter B (differential fuzzing of master vs 18.6, generator
`fz2.py`, seed 1, query 482).

## Summary

On PostgreSQL 19 (REL_19_STABLE, 19rc1) and master, `eval_const_expressions()` uses
NOT NULL constraints to fold `col IS NULL` / `col IS NOT NULL` / `bool IS [NOT] UNKNOWN` /
`ROW(...) IS NULL` to constants (PG19 commit e2debb64380 "Reduce Var IS [NOT] NULL quals
during constant folding" and its follow-ups cb7b7ec7, 0aaf0de7). Applied to the ON clause of a
FULL JOIN, this can turn a hash-joinable clause such as `(a.x IS NULL) = (b.y IS NULL)`
into a clause that only references one input (`NOT (b.y IS NULL)`). A FULL JOIN without
any hash- or merge-joinable clause cannot be planned, so a query that 18.x answers correctly
now fails with

    ERROR:  FULL JOIN is only supported with merge-joinable or hash-joinable join conditions

This is a regression (a query that worked stops working), not a wrong result. Upstream has
treated the same thing as a bug before: BUG #5263 (8.4) was a FULL JOIN broken by constant
folding of its ON clause, and it led to the "FULL JOIN ON FALSE" support.

## Minimal reproducer

```sql
CREATE TABLE fa (x int NOT NULL);
CREATE TABLE fb (y int);
INSERT INTO fa VALUES (0), (1);
INSERT INTO fb VALUES (0), (NULL);

SELECT * FROM fa FULL JOIN fb ON (fa.x IS NULL) = (fb.y IS NULL);
```

Full script with five variants: `B-01-full-join-notnull-folding.sql`.

## Actual vs expected

| | 18.6 | master 126976a8 (cassert), REL_19_STABLE code |
|---|---|---|
| `ON (fa.x IS NULL) = (fb.y IS NULL)` | 3 rows | ERROR FULL JOIN is only supported ... |
| `ON fb.y = (fa.x IS NULL)::int` | 3 rows | ERROR |
| `ON fb.flag = (fa.id IS NOT NULL)` (PRIMARY KEY column) | 4 rows | ERROR |
| `ON fb.flag = (fa.flag IS UNKNOWN)` (NOT NULL bool) | 4 rows | ERROR |
| `ON fb.flag = (ROW(fa.x, fa.id) IS NULL)` | 4 rows | ERROR |
| same as row 1 but LEFT JOIN | 2 rows | 2 rows (works) |

Expected (18.6 output, checked by hand): `fa.x` is NOT NULL, so `fa.x IS NULL` is false for
every fa row. The fa rows match the fb rows whose `y` is not NULL, and the fb row with
`y IS NULL` is null-extended:

```
 x | y
---+---
 0 | 0
 1 | 0
   |
```

The query is valid SQL and its result is well defined. The FULL JOIN limitation is a
documented implementation restriction, but here the planner itself creates it: the join
written by the user has a hash-joinable condition (18.6 plans it as `Hash Full Join`,
`Hash Cond: ((fa.x IS NULL) = (fb.y IS NULL))`), and the new folding destroys it.

## Versions

| Version | Result |
|---|---|
| 18.6 (REL_18_STABLE, release build) | works |
| master 20devel 126976a8 (23 Oct 2026, cassert) | fails |
| newest master (fetched 23 Oct 2026, same 126976a8) | fails (no fix in git log) |
| REL_19_STABLE fc189eb7 (19rc1) | same folding code present in clauses.c (lines 4076, 4163); not run, but the code path is identical |

## Root cause

`preprocess_qual_conditions()` (planner.c) runs `preprocess_expression()` →
`eval_const_expressions()` on every JoinExpr's quals, including FULL JOIN quals. In
`eval_const_expressions_mutator()`, case `T_NullTest` (clauses.c):

```c
if (!ntest->argisrow && arg &&
    expr_is_nonnullable(context->root, (Expr *) arg,
                        NOTNULL_SOURCE_HASHTABLE))
{
    ... IS_NULL -> false, IS_NOT_NULL -> true ...
    return makeBoolConst(result, false);
}
```

(The BooleanTest and the `ROW(...) IS [NOT] NULL` branches behave the same way.) The fold is
correct, but for a FULL JOIN it can leave `(false = (fb.y IS NULL))`, which simplifies to
`fb.y IS NOT NULL`. That clause mentions only `fb`, so `select_mergejoin_clauses()` and
`hash_inner_and_outer()` find no usable clause, and `add_paths_to_joinrel()` then has no path
for JOIN_FULL → `ereport(ERROR, "FULL JOIN is only supported with merge-joinable or
hash-joinable join conditions")`.

PG 18 had no NOT NULL-based folding in `eval_const_expressions()`; it only dropped
redundant `IS NOT NULL` base restrictions later, which never affected join clauses.

## Fix (patch attached: `B-01-full-join-notnull-folding.patch`, against master 126976a8)

Do not use NOT NULL proofs while preprocessing a FULL JOIN's ON clause. A new
`PlannerInfo.inFullJoinQuals` flag is set around `preprocess_expression()` for
`JOIN_FULL` quals in `preprocess_qual_conditions()`, and `var_is_nonnullable()` returns
false while it is set. Sub-selects inside the ON clause are planned with their own
PlannerInfo and are unaffected. The fold still happens everywhere else (WHERE, LEFT/INNER
join quals, and `reduce_outer_joins()` still turns `FULL JOIN ... WHERE a.notnull IS NULL`
into an anti join; checked with EXPLAIN).

The patch also adds a regression test to `join.sql` next to the FULL JOIN ON TRUE/FALSE
tests (plan is `Hash Full Join`, results as on 18).

Alternatives a reviewer may prefer:
1. Teach hash join to execute a FULL JOIN with no hash clauses (all tuples in one bucket;
   correct but O(n*m)). That would also fix the long-standing limitation for
   `FULL JOIN ... ON b.flag` and is more general, but it is a much larger change.
2. Fold, then keep the unfolded form if folding removed every potential hash/merge clause.
   This is more precise but needs the join's relids during preprocessing.

## How found, how verified

- Found by `fz2.py` (random nested LEFT/FULL/RIGHT joins, non-strict subquery outputs, IS NULL
  predicates; master 5433 vs 18.6 5435): 1 such diff in the first 500 queries. Two later runs of
  60,000 queries each filtered this error pattern out (occurrences were not counted).
- Minimal script `B-01-full-join-notnull-folding.sql` run 3 times, each on a freshly created
  database, on master and 18.6: master output md5 1ab45d51... (5 errors) every time, 18.6
  output md5 528f445d... (correct rows) every time.
- Patched build (tmp_install server on port 5440): output identical to 18.6.
- `make check` on the patched tree: all 239 tests pass (after a clean rebuild; the tree has no
  `--enable-depend`, so a PlannerInfo change needs `make clean`).

## Duplicate check

- Newest master `git log` (fetched 23 Oct 2026, head 126976a8): nothing touching FULL JOIN
  quals or the NullTest folding after the feature commits.
- pgsql-bugs/pgsql-hackers web search: no report of this error caused by NOT NULL
  folding. **Related active thread:** "[PG19] Wrong results from NOT NULL-based expression
  simplification" (pgsql-hackers, around 17 Oct 2026, message-id
  179220962657.1343374.11137544623255312817@gmail.com). It is about wrong results and
  ON CONFLICT failures from e2debb64380, and mentions a patch that "lost a FULL JOIN pushdown".
  We could not open the archive (postgresql.org blocked from our sandbox), so **read that
  thread before filing**. If its patch reworks the folding, post this case there as a reply
  instead of filing a new bug.

## Draft text for the pgsql-bugs form

> Subject: PG19 regression: FULL JOIN fails after NOT NULL-based IS NULL folding
>
> PostgreSQL version: 19rc1 / master 126976a8 (18.6 works)
>
>     CREATE TABLE fa (x int NOT NULL);
>     CREATE TABLE fb (y int);
>     INSERT INTO fa VALUES (0), (1);
>     INSERT INTO fb VALUES (0), (NULL);
>     SELECT * FROM fa FULL JOIN fb ON (fa.x IS NULL) = (fb.y IS NULL);
>
> 18.6 returns 3 rows (Hash Full Join on `(fa.x IS NULL) = (fb.y IS NULL)`). 19 and master
> fail with "FULL JOIN is only supported with merge-joinable or hash-joinable join
> conditions". eval_const_expressions() now folds `fa.x IS NULL` to false using the NOT NULL
> constraint (e2debb64380), which leaves `fb.y IS NOT NULL`. That clause no longer references
> fa, so the FULL JOIN has no hashable clause. The same happens with `IS NOT NULL` on a primary
> key, `bool IS UNKNOWN` on a NOT NULL boolean, and `ROW(...) IS NULL`.
>
> A possible fix (patch attached): do not use NOT NULL proofs while preprocessing FULL JOIN
> quals. It passes make check. Found with a differential (18 vs 19) query fuzzer.
