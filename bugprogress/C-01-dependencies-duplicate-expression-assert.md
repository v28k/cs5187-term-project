# C-01: assertion failure in dependencies_clauselist_selectivity() when two clauses use the same statistics expression

Status: **confirmed (3/3 on master cassert, 3/3 on 18.6 cassert), root-caused, patch
written and regression-tested. NOT YET FILED.**
Found 23 Oct 2026 by hunter C (extended-statistics clause fuzzer, a mutation of
BUG #19789 / #19772).

## Summary

With functional-dependency statistics on an expression (`CREATE STATISTICS ...
(dependencies) ON a, (b + 1)`), a WHERE clause list that contains two different
clauses on the same expression, e.g. `(b + 1) = 2 AND (b + 1) IN (2, 3)`, or even
the same BooleanTest twice (`(c IS TRUE) AND (c IS TRUE)`), crashes an
assert-enabled server during planning:

    TRAP: failed Assert("AttrNumberIsForUserDefinedAttr(list_attnums[i]) ||
          !bms_is_member(attnum, clauses_attnums)"), File: "dependencies.c", Line: 1504

`dependencies_clauselist_selectivity()` deliberately gives a duplicate expression the
same (negative) attnum as its first occurrence ("If the expression is duplicate, use
the same attnum"), and `clauselist_apply_dependencies()` explicitly collects *all*
clauses with the same attnum and estimates them together. The assertion a few lines
later, which claims "expressions are unique", contradicts both. Release builds are
not affected (no wrong result, no crash); it is an assertion-only bug, but it kills
the backend (and restarts the cluster) on every assert-enabled build, including
the buildfarm and developers' test servers, with a one-line query.

## Minimal reproducer

`C-01-dependencies-duplicate-expression-assert.sql`:

```sql
CREATE TABLE dt (a int, b int);
INSERT INTO dt SELECT x % 10, x % 10 FROM generate_series(1, 1000) x;
CREATE STATISTICS dt_deps (dependencies) ON a, (b + 1) FROM dt;
ANALYZE dt;
EXPLAIN SELECT * FROM dt WHERE a = 1 AND (b + 1) = 2 AND (b + 1) IN (2, 3);
```

A second form (expression statistics on a BooleanTest, clause repeated, as it can be
when a view or ORM adds a predicate that is already present; duplicate BooleanTests
are not removed by the planner):

```sql
CREATE TABLE dt2 (a int, c bool);
INSERT INTO dt2 SELECT x % 10, x % 10 < 5 FROM generate_series(1, 1000) x;
CREATE STATISTICS dt2_deps (dependencies) ON a, (c IS TRUE) FROM dt2;
ANALYZE dt2;
EXPLAIN SELECT * FROM dt2 WHERE a = 1 AND (c IS TRUE) AND (c IS TRUE);
```

The columns must be correlated so that ANALYZE stores at least one dependency
(with uncorrelated data, e.g. `x % 3 = 0`, the dependency list is empty and the
function returns before reaching the assertion). Both forms crash 18.6 (cassert).

Note: `(b + 1) = 2 AND (b + 1) = 3` does not reach the code on master, because the
equivalence-class machinery proves it contradictory first; `= 2 AND IN (2, 3)` does.

## Actual vs expected

| Build | Result |
|---|---|
| master 126976a8 (23 Oct 2026, cassert) | backend killed by the TRAP above, server restarts |
| 18.6 (REL_18_STABLE, built with --enable-cassert) | same TRAP (dependencies.c line 1525) |
| 18.6 release build (no asserts) | `Seq Scan on dt (rows=20)`, no error |
| master with the patch below | `Seq Scan on dt (rows=20)`, same estimate as the release build |

Expected: the query plans normally. An assertion must hold for every reachable
input; here the code itself (the de-duplication loop and
`clauselist_apply_dependencies`) is designed to handle several clauses per attnum,
and does so correctly for plain columns (`a = 1 AND b = 2 AND b IN (2, 3)` with
`(dependencies) ON a, b` does not trip anything, since the assertion exempts
user-column attnums). Only the expression branch of the assertion is wrong.

## Versions

- master 126976a8 (newest master as of 23 Oct 2026; `git fetch` returned the same
  head): affected (3/3 crashes on fresh databases).
- 18.6, cassert build of REL_18_STABLE: affected (3/3 crashes on fresh databases).
- The code (expressions in extended statistics, the de-duplication loop and the
  assertion) was added in PostgreSQL 14 by commit a4d75c86bf ("Extended statistics
  on expressions", 27 Mar 2021), so 14-17 are expected to be affected the same way
  (not run; our master clone is too shallow to show that commit, the hash comes from
  the pgsql-committers announcement).

## Root cause

`src/backend/statistics/dependencies.c`, `dependencies_clauselist_selectivity()`:

```c
			else if (dependency_is_compatible_expression(clause, rel->relid,
														 rel->statlist,
														 &expr))
			{
				/* special attnum assigned to this expression */
				attnum = InvalidAttrNumber;
				...
				/* If the expression is duplicate, use the same attnum. */
				for (int i = 0; i < unique_exprs_cnt; i++)
				{
					if (equal(unique_exprs[i], expr))
					{
						/* negative attribute number to expression */
						attnum = -(i + 1);
						break;
					}
				}
	...
	for (int i = 0; i < list_length(clauses); i++)
	{
		...
		attnum = list_attnums[i] + attnum_offset;

		/*
		 * Either it's a regular attribute, or it's an expression, in which
		 * case we must not have seen it before (expressions are unique).
		 ...
		 */
		Assert(AttrNumberIsForUserDefinedAttr(list_attnums[i]) ||
			   !bms_is_member(attnum, clauses_attnums));
```

The second clause on `(b + 1)` gets the same attnum as the first, so the attnum is
already in `clauses_attnums` and the assertion fails. "Expressions are unique" is
true of `unique_exprs[]`, not of the clause list. The consumer handles duplicates:

```c
	/* clauselist_apply_dependencies() */
		foreach(l, clauses)
		{
			...
			if (list_attnums[listidx] == i)
			{
				attr_clauses = lappend(attr_clauses, clause);
				*estimatedclauses = bms_add_member(*estimatedclauses, listidx);
			}
		}
		simple_sel = clauselist_selectivity_ext(root, attr_clauses, ...);
```

So removing the assertion is the complete fix; nothing downstream relies on it.

## Fix (patch attached)

`C-01-dependencies-duplicate-expression-assert.patch` (against master 126976a8):
removes the incorrect assertion and its comment, documents that several clauses may
share an attnum, and adds a regression test to `stats_ext.sql` (after the existing
"OR clauses referencing different attributes" test on the expression statistics):

```sql
-- multiple clauses referencing the same expression
SELECT * FROM check_estimated_rows('SELECT * FROM functional_dependencies WHERE (a * 2) = 2 AND (a * 2) IN (2, 102) AND upper(b) = ''1''');
```

Without the fix this test crashes the assert-enabled server; with it the estimate is
1 row (the two clauses on `a * 2` are estimated together, as for a plain column).

Verification: patched master rebuilt and installed, `make installcheck-parallel`:
all 239 tests passed (before updating `expected/stats_ext.out` the only difference
was the new test's output).

## How found, how verified

- Method C (b): mutation of the two extended-statistics bugs reported this month,
  BUG #19789 (MCV + boolean domain, "expression not found in statistics object") and
  BUG #19772 ("corrupt MVNDistinct entry"). Script `xstats.py` (hunter C scratch):
  a table with domain, expression and plain columns, ten random `CREATE STATISTICS`
  objects (random kinds, columns and expressions), then 4000 random EXPLAINs per seed
  (AND/OR/NOT combinations of ~60 clause atoms, GROUP BY, ROLLUP, DISTINCT, joins).
  Oracle: SQLSTATE XX000 or a lost connection. Six seeds: the two known errors
  (#19789, #19772) plus two crashes, both this TRAP.
- Reduced by hand to the 5-statement script above.
- Reproduced 3/3 on fresh databases on master 126976a8 (cassert), 3/3 on 18.6
  (cassert); release 18.6 shows no symptom.

## Duplicate check

- `git log` of the newest master (126976a8) for `dependencies.c`: no related change;
  the assertion is unchanged since PostgreSQL 14.
- pgsql-bugs (via the GitHub mirror of the list, Sep-Oct 2026, and web search for the
  assertion text): no report. The same assertion text appears once in a 2024
  pgsql-hackers backtrace in the "POC, WIP: OR-clause support for indexes" thread
  (https://www.mail-archive.com/pgsql-hackers@lists.postgresql.org/msg174242.html),
  where it was hit while testing an unpublished patch; we could not open the thread
  from this environment, and the assertion was never changed, so it was apparently not
  recognised as a bug in released code. Mention this thread in the report.
- Not the same as BUG #19789 (MCV path, `mcv_get_match_bitmap`, domain RelabelType)
  or BUG #19772 (ndistinct path): different file, function and trigger.

## Draft text for the pgsql-bugs form

> Subject: Assertion failure in dependencies_clauselist_selectivity with two clauses on the same statistics expression
>
> PostgreSQL version: 18.6 (cassert build); also master 126976a8. Code from 14.
>
>     CREATE TABLE dt (a int, b int);
>     INSERT INTO dt SELECT x % 10, x % 10 FROM generate_series(1, 1000) x;
>     CREATE STATISTICS dt_deps (dependencies) ON a, (b + 1) FROM dt;
>     ANALYZE dt;
>     EXPLAIN SELECT * FROM dt WHERE a = 1 AND (b + 1) = 2 AND (b + 1) IN (2, 3);
>
> On an assert-enabled build this fails with
> TRAP: failed Assert("AttrNumberIsForUserDefinedAttr(list_attnums[i]) || !bms_is_member(attnum, clauses_attnums)"), File: "dependencies.c".
> `WHERE a = 1 AND (c IS TRUE) AND (c IS TRUE)` with statistics on `a, (c IS TRUE)` fails the same way.
> Release builds produce a normal plan.
>
> dependencies_clauselist_selectivity() deliberately assigns a duplicate expression
> the same attnum as its first occurrence, and clauselist_apply_dependencies()
> estimates all clauses with the same attnum together, but the assertion claims that
> an expression attnum is never seen twice. The attached patch removes the assertion
> (nothing relies on it) and adds a regression test to stats_ext. Found with a
> fuzzer for extended statistics.
