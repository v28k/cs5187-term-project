# BUG-02: range containment with a NULL element returns true/false instead of NULL

Status: **filed 23 Oct 2026 by Venu Kummari as BUG #19793** (patch sent as a reply). Found, reproduced on 18.6 and master, root-caused, patch written.
Found 23 Oct 2026 by the new metamorphic oracle (`expr:scalar_sub` rewrite), in
the first 150 test cases it ever ran.

## One-paragraph summary

Since PostgreSQL 17, the planner support functions for `elem <@ range` and
`range @> elem` (`elem_contained_by_range_support`,
`range_contains_elem_support` -> `find_simplified_clause()` in
`src/backend/utils/adt/rangetypes.c`) replace the call by a **constant** when
the range is a constant that is empty (`false`) or unbounded on both sides
(`true`). Both operators are strict, so for a NULL element the correct result
is NULL. The constant is wrong wherever NULL and false/true are distinguished:
in the select list, under `NOT`, in `IS NULL` / `IS DISTINCT FROM` tests,
`CASE`, `COALESCE`, and in outer-join or `NOT IN` logic built on top of it.
It is a **silent wrong result** in released versions.

## Minimal reproducer (copy-paste)

```sql
SELECT c,
       '(,)'::int4range @> c       AS unbounded_contains,   -- expected NULL for c = NULL
       c <@ '(,)'::int4range       AS unbounded_contained,  -- expected NULL
       'empty'::int4range @> c     AS empty_contains,       -- expected NULL
       NOT ('empty'::int4range @> c) AS not_empty           -- expected NULL
FROM (VALUES (NULL::int), (1)) v(c);
```

Actual on 18.6 and master (`\pset null NULL`):

```
  c   | unbounded_contains | unbounded_contained | empty_contains | not_empty
------+--------------------+---------------------+----------------+-----------
 NULL | t                  | t                   | f              | t
 1    | t                  | t                   | f              | t
```

Expected: the NULL row gives `NULL | NULL | NULL | NULL`.

The plan shows the simplification:

```sql
EXPLAIN (VERBOSE, COSTS OFF) SELECT '(,)'::int4range @> c FROM (VALUES (NULL::int), (1)) v(c);
--  Values Scan on "*VALUES*"
--    Output: true
```

Proof the operator itself is strict (no planner simplification, same values):
`SELECT (SELECT '(,)'::int4range) @> NULL::int;` returns NULL.
Note: with a single-row `VALUES` the planner folds the whole expression with
the NULL constant and the bug hides; use two rows or a table column.

A realistic query where it matters (outer join, from the fuzzer):

```sql
-- v0/tl from src/corpus/schema.sql; any LEFT JOIN with unmatched rows works
SELECT a3.c0, a4.c0, ('(,)'::int4range @> a4.c0) AS plain,
       ((SELECT '(,)'::int4range) @> a4.c0) AS via_subselect
FROM v0 AS a3 LEFT JOIN tl AS a4 ON a3.c0 = a4.c0;
-- unmatched rows: plain = t, via_subselect = NULL  (the two must be equal)
```

## Versions

| Version | Result |
|---|---|
| PostgreSQL 18.6 (REL_18_STABLE `92d47d5`, release build) | wrong (`t`, `t`, `f`, `t` for the NULL row) |
| master 20devel `26bd08fb` (16 Oct 2026, cassert) | wrong (same) |
| REL_17_STABLE | same code present (`range_contains_elem_support` exists) -> affected, not run |
| REL_16_STABLE | support functions do not exist -> not affected |

The support functions were added in PostgreSQL 17 (planner support for range
containment, so `col <@ const_range` can use btree bounds).

## Root cause

`find_simplified_clause()`:

```c
	if (empty)
	{
		/* if the range is empty, then there can be no matches */
		return makeBoolConst(false, false);
	}
	else if (lower.infinite && upper.infinite)
	{
		/* the range has infinite bounds, so it matches everything */
		return makeBoolConst(true, false);
	}
```

ignores `elemExpr` completely. For the bounded cases it builds
`elem >= lower AND elem < upper`, which is NULL-correct; only these two
constant cases lose strictness.

## Fix (patch attached)

`0001-Don-t-reduce-range-containment-with-a-nullable-eleme.patch`, against
master `26bd08fb`:

```c
	if (empty || (lower.infinite && upper.infinite))
	{
		/* ... the operators are strict, so a NULL element yields NULL ... */
		if (!expr_is_nonnullable(root, elemExpr, NOTNULL_SOURCE_HASHTABLE))
			return NULL;
		return makeBoolConst(!empty, false);
	}
```

`expr_is_nonnullable()` (optimizer/util/clauses.c) already handles `root ==
NULL`. With the patch the constant is still produced when the element is
provably non-null (e.g. `coalesce(c, 0)`), and the expression is left alone
otherwise.

Regression tests added to `src/test/regress/sql/rangetypes.sql` (NULL row
returns NULL; non-null element still folds). Two existing expected outputs
change: `current_date <@ daterange 'empty'` and
`current_date <@ daterange(NULL, NULL)` are no longer folded to `false`/`true`,
because `expr_is_nonnullable()` does not know `CURRENT_DATE` is never NULL.
A reviewer may prefer to teach `expr_is_nonnullable()` about the date/time
`SQLValueFunction`s (`CURRENT_DATE`, `CURRENT_TIMESTAMP`, `LOCALTIMESTAMP`, ...;
not `CURRENT_SCHEMA`, which can be NULL) to keep those folded. Mention this
in the report.

Verification done: full `make check` on the patched tree: the only failing
test before updating the expected file was `rangetypes`, with exactly the
intended differences (shown in the patch). Re-run `make check` once more after
applying the patch on a fresh checkout before posting.

## How it was found (for the paper)

The grammar generated (test case 112, seed 7, `configs`: metamorphic on):

```sql
SELECT (FALSE AND ('0'::text LIKE ''::text)) AS c0, MAX('2000-01-01 00:00:00+00'::timestamptz) AS c1
FROM tl AS a1, LATERAL (SELECT 10.0::numeric AS c0, '1970-01-01'::date AS c1) AS a2 GROUP BY a2.c0
UNION
SELECT (COALESCE('(,)'::int4range, '(,5]'::int4range) @> a4.c0) AS c0, TO_TIMESTAMP((a3.c0 % 100000)) AS c1
FROM (v0 AS a3 LEFT OUTER JOIN tl AS a4 ON (a3.c0 = a4.c0));
```

The `expr:scalar_sub` rewrite replaced the typed node `expr<int4range>` =
`'(,)'::int4range` by `(SELECT ('(,)'::int4range))`. That blocks the
simplification, so the rewritten query returned NULL where the original
returned `t` for the three null-extended rows. Both sides were re-run and gave
the same digests again (confirmed, not flaky). Evidence:
`evidence/bug02-original-fuzzer-testcase.sql`,
`evidence/bug02-original-oracle-verdict.json`.

## Checklist before filing

1. Search pgsql-bugs / pgsql-hackers for "range_contains_elem_support",
   "elem_contained_by_range_support", "find_simplified_clause", "range @> NULL".
   (A web search on 23 Oct 2026 found nothing.)
2. Re-run the reproducer on the newest 17.x, 18.x and master.
3. File via https://www.postgresql.org/account/submitbug/ with the
   "Minimal reproducer", "Versions" and a two-sentence root cause.
4. Reply in the thread with the patch (or post it to pgsql-hackers referencing
   the bug number).

## Draft report text

> Subject: Range containment support function returns true/false for a NULL element
>
> PostgreSQL version: 18.6 (also master 26bd08fb; code present since 17)
>
>     SELECT c, '(,)'::int4range @> c, NOT ('empty'::int4range @> c)
>     FROM (VALUES (NULL::int), (1)) v(c);
>
> returns `t` and `t` for the NULL row; both should be NULL, since
> range_contains_elem / elem_contained_by_range are strict (with a
> sub-select around the range, which blocks the planner simplification, the
> result is NULL). EXPLAIN VERBOSE shows the expression replaced by the
> constant `true`.
>
> find_simplified_clause() in rangetypes.c returns makeBoolConst(false) for an
> empty constant range and makeBoolConst(true) for an unbounded one without
> considering that the element may be NULL. The attached patch only reduces to
> a constant when expr_is_nonnullable() proves the element non-null, and adds
> regression tests. Found with a metamorphic (equivalent-expression) fuzzer.

## Re-verification, 23 Oct 2026 (just before filing)

Reproduced again from a fresh session on:

| Build | Result |
|---|---|
| master 126976a8 (23 Oct 2026, newest at the time; cassert) | bug present |
| REL_18_STABLE 9412c35 (newest 18.x branch head; cassert) | bug present |
| 18.6 release | bug present |

Newest master's git log has no commit touching this code since the bug was found,
and a web search of pgsql-bugs on 23 Oct found no existing report, so it is not a
duplicate and not fixed upstream yet.
