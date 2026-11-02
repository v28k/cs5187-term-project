# E-02: "plan should not reference subplan's variable" with Memoize and a correlated ALL/ANY sublink (master regression from f8da64e6)

Status: **reproduced with default settings on master 633dee1b (2 Nov 2026); bisected to
f8da64e6 (reverting it alone fixes the query); root-caused; patch with regression test,
`make check` 239/239. Duplicate search: none found (2 Nov 2026). FILED on pgsql-bugs (2 Nov 2026), patch sent as a reply with Richard Guo in Cc; bug number to be added.**
Found by our fuzzer (internal-error oracle, hunt on newest master, candidate `342fb8c219dd`),
then reduced by hand from a 2-statement test case to one join.

## Summary

Since commit f8da64e6 ("Make cache keys of other Params a Memoize subplan depends on",
Richard Guo, 2 Nov 2026), a query whose memoized inner relation has a qual containing a
correlated ALL/ANY sublink fails at plan time:

    ERROR:  plan should not reference subplan's variable

The reproducer (`E-02-memoize-subplan-param.sql`) uses default settings:

    SELECT count(*) FROM d_a a JOIN d_b b ON a.x = b.x WHERE 5 > ALL (SELECT b.x);

| Build | Result |
|---|---|
| master 633dee1b | **ERROR: plan should not reference subplan's variable** |
| master 633dee1b with f8da64e6 reverted | 400 |
| master 126976a8 (before f8da64e6) | 400 |
| 18.6 | 400 |
| 633dee1b + patch | 400 |

## Root cause

f8da64e6 makes `paraminfo_get_equal_hashops()` collect every PARAM_EXEC Param in the inner
relation's base quals and targetlist with `pull_exec_params_walker()`, and make each a
cache key. The walker also descends into SubPlans. For `5 > ALL (SELECT b.x)` the SubPlan's
testexpr is `5 > $n`, where `$n` stands for the subplan's own output column and is set by
the subplan itself. Making `$n` a cache key puts a reference to it in the Memoize node,
above the scan that runs the subplan, so `finalize_plan()` finds a Param that is not valid
at that level and raises the error.

## Fix

`v1-0001-Dont-make-a-SubPlans-output-Params-Memoize-cache-keys.patch`: in
`pull_exec_params_walker()`, for a SubPlan only walk its `args` (which are evaluated in the
memoized relation's context), not its testexpr. Adds a regression test to `memoize.sql`
(nested loop + Memoize over tenk1 with `5 > ALL (SELECT t2.unique1)`; the plan keeps
Memoize with cache key `t1.twenty` and the SubPlan as a filter, count 250).

## How we found it

Our fuzzer ran on the newest master (633dee1b, assertions on) with the Grammar+Oracles
configuration. The internal-error oracle flagged XX000 "plan should not reference subplan's
variable" on an `INSERT ... SELECT ... EXCEPT SELECT ... WHERE '(,5]'::int4range > ALL
(SELECT CASE WHEN '[0,0]'::int4range @> a5.c0 ...)`. Running the query under our plan
variants showed that it fails only with a nested-loop plan; reduction gave
`... JOIN ... WHERE 5 > ALL (SELECT b.x)`, and `enable_memoize = off` removes the error.
We then built 633dee1b with f8da64e6 reverted to confirm the cause.

## Draft for https://www.postgresql.org/account/submitbug/

- PostgreSQL version: newest in the list (the report says master)
- Operating system: Ubuntu 24.04, x86_64
- Short description: `"plan should not reference subplan's variable" with Memoize since f8da64e6`

```
PostgreSQL version: master (20devel) 633dee1b, built from source with
assertions. Operating system: Ubuntu 24.04, x86_64.

Since commit f8da64e6 ("Make cache keys of other Params a Memoize subplan
depends on"), a correlated ALL/ANY sublink in the quals of a memoized
relation makes planning fail, with default settings:

CREATE TABLE d_a (x int NOT NULL);
CREATE TABLE d_b (x int, pad text);
INSERT INTO d_a SELECT g % 10 FROM generate_series(1, 1000) g;
INSERT INTO d_b SELECT g, repeat('x', 100) FROM generate_series(1, 100000) g;
CREATE INDEX ON d_b (x);
VACUUM ANALYZE d_a, d_b;

SELECT count(*) FROM d_a a JOIN d_b b ON a.x = b.x WHERE 5 > ALL (SELECT b.x);
ERROR:  plan should not reference subplan's variable

Expected: 400 (the result with enable_memoize = off, on 126976a8, and with
f8da64e6 reverted).

Cause: paraminfo_get_equal_hashops() now collects every PARAM_EXEC Param in
the inner relation's base quals and targetlist with
pull_exec_params_walker() and makes it a cache key. The walker descends into
SubPlans, so the Param in the SubPlan's testexpr (5 > $n), which stands for
the subplan's own output and is set by the subplan itself, also becomes a
cache key. The Memoize node then references a Param that only its child
sets, and finalize_plan() raises the error.

I will reply with a patch that, for a SubPlan, walks only its args (which
are evaluated in the memoized relation's context), with a regression test
in memoize.sql; make check passes.

Found with a grammar-based fuzzer for PostgreSQL.
```

After the report email arrives, reply-all with the patch and add Richard Guo
<guofenglinux@gmail.com> (author of f8da64e6) to Cc. Reply body:

```
Hi,

Attached is a patch. pull_exec_params_walker() now walks only the args of a
SubPlan, which are evaluated in the memoized relation's context, and not its
testexpr, whose Params are set by the subplan itself. With the patch the
reproducer returns 400, and Memoize is still used (cache key a.x, with the
SubPlan as a filter on the inner scan).

The patch adds a regression test to memoize.sql (nested loop with Memoize
over tenk1 and 5 > ALL (SELECT t2.unique1)). make check passes (239/239).

Richard, Cc'ing you as the author of f8da64e6.

Regards,
Venu Kummari
```
