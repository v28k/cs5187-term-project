# BUG-01: JSON_TABLE does not assign collations to its context item and PASSING arguments

Status: **found, reproduced, root-caused, patch written, regression tests pass. Not yet filed.**

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

Affected: every branch with JSON_TABLE (17, 18, 19 beta, master). REL_17 has
the same code (`parse_jsontable.c`: `tf->docexpr = transformExpr(...)` with no
`assign_expr_collations`).

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

Patch with regression tests: [`0001-Assign-collations-to-JSON_TABLE-s-context-item-and-P.patch`](0001-Assign-collations-to-JSON_TABLE-s-context-item-and-P.patch)
(against master `26bd08fb`). Checked: the new tests fail on unpatched 18.6
(wrong result and collation errors) and pass with the patch; the SQL/JSON,
json, jsonb, jsonpath and collate regression suites pass.

## How to file it (to do)

1. Bug report: https://www.postgresql.org/account/submitbug/ (needs a free
   community account), or mail `pgsql-bugs@lists.postgresql.org`. Paste the
   "Minimal reproducer" and "Symptoms" sections, the versions, and the root
   cause in two sentences.
2. Patch: reply in the same thread with the `.patch` file attached (or post to
   `pgsql-hackers` referencing the bug number).
3. Record the bug number, thread URL, and any fix commit here.

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
