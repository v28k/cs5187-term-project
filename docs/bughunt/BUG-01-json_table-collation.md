# BUG-01: JSON_TABLE does not assign collations to its context item and PASSING arguments

Status: **reported upstream as BUG #19768 (official bug form). v1 patch
prepared and verified; to be attached to the #19768 email thread.**

Found 16 Oct 2026 by the grammar campaign (`configs/cloud_hunt.yaml`, trial 0,
test case 13306, about 600 s into the run), as an assertion failure on the
assert-enabled master build.

## Symptoms

| Build | Query | Result |
|---|---|---|
| master `26bd08fb` (cassert) | row comparison in the context item | server crash: `TRAP: failed Assert("list_length(rcexpr->inputcollids) == nopers"), File: "execExpr.c", Line: 2078` |
| 18.6 release | same | **wrong result**: `ROW(1, 2) < ROW(3, 4)` evaluates to `false` |
| 18.6 release | text comparison in the context item or PASSING, even with explicit `COLLATE "C"` | spurious `ERROR: could not determine which collation to use for string comparison` |
| master (cassert) | row comparison in PASSING | server crash (same assertion) |
| 17.11 / 18.6 release | row comparison in PASSING | `t` (correct by chance; the expression still has no collation) |
| 17.11 release | context item and text cases above | same wrong result and collation errors as 18.6 |

The wrong row-comparison result is "the result for equal rows": with an empty
`inputcollids` the executor compares zero columns, so `<`/`>` give `false` and
`<=`/`>=` give `true` whatever the values (also with table columns, not only
constants).

Affected: every branch with JSON_TABLE (17, 18, 19 beta, master). Reproduced
on 17.11 (`REL_17_STABLE` `e4cc408`), 18.6 (`REL_18_STABLE` `92d47d5`) and
master `26bd08fb`, all built from source; script
[`evidence/bug01-repro.sql`](evidence/bug01-repro.sql), output
[`evidence/bug01-v1-repro-results.txt`](evidence/bug01-v1-repro-results.txt).

## Minimal reproducer

```sql
-- Expected t (ROW(1,2) < ROW(3,4) is true). 18.6 returns f; assert builds crash.
SELECT * FROM JSON_TABLE(jsonb_build_object('k', ROW(1, 2) < ROW(3, 4)), '$'
       COLUMNS (a bool PATH '$.k'));

-- Expected t. 18.6: ERROR: could not determine which collation to use for string comparison
SELECT * FROM JSON_TABLE(jsonb_build_object('k', 'a' < 'b' COLLATE "C"), '$'
       COLUMNS (a bool PATH '$.k'));

-- Expected t. 18.6: same collation error.
SELECT * FROM JSON_TABLE(jsonb '{}', '$' PASSING 'a' < 'b' COLLATE "C" AS x
       COLUMNS (a bool PATH '$x'));
```

The same expressions outside JSON_TABLE (`SELECT ROW(1,2) < ROW(3,4)`, or
inside `JSON_QUERY(...)`) work.

## Root cause

`transformJsonTable()` (`src/backend/parser/parse_jsontable.c`) transforms the
context item and PASSING arguments into `TableFunc.docexpr` with
`transformExpr()` and copies the PASSING values into `tf->passingvalexprs`, but
never calls `assign_expr_collations()` on them. The column expressions do get
it (`transformJsonTableColumns`), and so does XMLTABLE's document expression
(`transformRangeTableFunc` in `parse_clause.c`). A FROM-clause function is not
covered by the query-level collation pass, so the expressions keep
`InvalidOid` collations:

* a `RowCompareExpr` keeps `inputcollids = NIL`; `ExecInitExprRec()` walks the
  operators together with that list, so it compiles **zero** column
  comparisons and the result is `false` (the assertion catches it on cassert
  builds);
* a text comparison reaches `varstr_cmp()` with no collation and errors out.

## Fix

One line, after the context item is transformed (before the PASSING values are
copied, so the copies are collated too):

```c
	tf->docexpr = transformExpr(pstate, (Node *) jfe, EXPR_KIND_FROM_FUNCTION);
+	assign_expr_collations(pstate, tf->docexpr);
```

**Patch to send:** [`v1-0001-Assign-collations-to-JSON_TABLE-s-context-item-an.patch`](v1-0001-Assign-collations-to-JSON_TABLE-s-context-item-an.patch)
(author Venu Kummari <venu2805k@gmail.com>, against master `26bd08fb`,
`Bug: #19768` trailer). Its code and tests are byte-identical to the earlier
[`0001-...patch`](0001-Assign-collations-to-JSON_TABLE-s-context-item-and-P.patch),
which is kept for history; v1 only changes the author line and makes the
commit message precise (zero-column comparison returns the equal-rows result,
not always false) and adds the bug number.

Checks run on the v1 commit (16 Oct 2026):

| Check | Result |
|---|---|
| `git am` onto clean upstream master `26bd08fb` | applies; resulting tree identical to the tested tree (`57b481dd`) |
| `make check` (core regression suite, cassert build) | **All 239 tests passed**, incl. `sqljson_jsontable` and `collate`: [`evidence/bug01-v1-make-check.log`](evidence/bug01-v1-make-check.log) |
| `pgindent --diff src/backend/parser/parse_jsontable.c` | no changes (tool confirmed working on a mis-indented copy) |
| `git diff --check` | no whitespace errors |
| Reproducers: unpatched 17.11 / 18.6, patched master | bug on 17.11 and 18.6; all four `t` with the patch |
| Code hunk on `REL_18_STABLE` / `REL_17_STABLE` | applies; the test-file hunk needs context adjustment (left to the committer's back-patch) |

Not run: `make check-world`, and the full regression suites on 17/18 with the
fix back-ported.

## Filing status

1. Bug report: **BUG #19768**, filed through
   https://www.postgresql.org/account/submitbug/.
2. Patch: reply to the #19768 thread on `pgsql-bugs` (plain text, inline
   reply) with the v1 patch attached. A revised patch is sent as `v2-0001-...`
   in the same thread.
3. To record here: thread URL (message-id), reviewers' comments, fix commit
   hash and branches.

## Draft report text

> Subject: JSON_TABLE: row/text comparisons in context item or PASSING give wrong results / collation errors
>
> PostgreSQL version: 18.6 (also reproduced on master at 26bd08fb; same code in 17)
>
> SELECT * FROM JSON_TABLE(jsonb_build_object('k', ROW(1, 2) < ROW(3, 4)), '$' COLUMNS (a bool PATH '$.k'));
>
> returns `f`, but `ROW(1, 2) < ROW(3, 4)` is true. On an assert-enabled build
> the same query fails `Assert("list_length(rcexpr->inputcollids) == nopers")`
> in execExpr.c. A text comparison in the same place, e.g.
> `jsonb_build_object('k', 'a' < 'b' COLLATE "C")`, or in a PASSING argument,
> fails with "could not determine which collation to use for string
> comparison".
>
> transformJsonTable() never runs assign_expr_collations() on the transformed
> context item / PASSING arguments (XMLTABLE does, in transformRangeTableFunc),
> so these expressions keep no collation; a RowCompareExpr ends up with an empty
> inputcollids list and ExecInitExprRec compiles zero column comparisons.
> Attached patch adds the call, with regression tests.
