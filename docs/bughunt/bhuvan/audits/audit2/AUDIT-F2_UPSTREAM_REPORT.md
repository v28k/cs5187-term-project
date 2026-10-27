# Draft report for pgsql-bugs (not sent)

> Draft only. Nothing has been posted. The user must review and approve it
> before anything goes upstream.

**Subject:** first_value()/nth_value() IGNORE NULLS loop forever with EXCLUDE GROUP/TIES and no ORDER BY

**PostgreSQL version:** 19 (current REL_19_STABLE tip 015f4c9fc3; also
fc189eb750) and master (20devel, 126976a8ff). 18 and earlier don't have
IGNORE NULLS. No commit touches nodeWindowAgg.c between these revisions.

**Platform:** x86_64 Linux (Ubuntu 24.04 under WSL2), gcc 13.3.0, built with
`--enable-cassert --enable-debug`. The bug is in executor logic, so I don't
expect it to depend on the platform.

## Description

A window function call with IGNORE NULLS never returns when all of these hold:

* the function scans the frame forward: `first_value()` or `nth_value()`;
* the window has no ORDER BY;
* the frame ends at UNBOUNDED FOLLOWING, or at a ROWS offset far beyond the
  partition (`1000000000000 FOLLOWING` hangs the same way);
* the frame uses EXCLUDE GROUP, or uses EXCLUDE TIES while the current row
  doesn't supply the requested non-null value.

The backend then spins at 100% CPU in `ignorenulls_getfuncarginframe()` and
never checks for interrupts. statement_timeout, `pg_cancel_backend()`,
`pg_terminate_backend()` and `pg_ctl stop -m fast` don't stop it (each tested
separately). The only way out is SIGKILL, which makes the postmaster restart
all sessions. The stuck backend also never absorbs a ProcSignalBarrier: an
`ALTER DATABASE other_db SET TABLESPACE` that completes in ~0.2 s normally
instead blocked indefinitely (killed after 12 s) while the backend ran,
waiting on `IPC / ProcSignalBarrier`. Any user who can run a SELECT can
trigger it, with no table and no special privilege.

## How to reproduce

No tables or settings are needed:

```sql
SET statement_timeout = '5s';
SELECT first_value(x) IGNORE NULLS OVER w
FROM (VALUES (1)) v(x)
WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP);
```

**Expected:** one row containing NULL, at once. With no ORDER BY every row is
a peer of the current row, so EXCLUDE GROUP leaves the frame empty. The same
query without IGNORE NULLS returns NULL. So does the aggregate-path
equivalent, `(array_agg(x) FILTER (WHERE x IS NOT NULL) OVER w)[1]`.

**Actual:** the query never finishes. After 10 seconds (5 s past the timeout):

```
 state  | wait_event_type | wait_event | secs
--------+-----------------+------------+------
 active |                 |            |   10
```

The backend was still `active` after `pg_cancel_backend()` and again after
`pg_terminate_backend()`. `pg_ctl stop -m fast -t 30` reported "server does
not shut down".

These variants hang the same way:

```sql
-- EXCLUDE TIES; the NULL row never finishes (expected: NULL, then 2)
SELECT x, first_value(x) IGNORE NULLS
       OVER (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE TIES)
FROM (VALUES (NULL::int), (2)) v(x);

-- nth_value (expected: NULL, NULL)
SELECT nth_value(x, 2) IGNORE NULLS
       OVER (ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING EXCLUDE TIES)
FROM (VALUES (1), (2)) v(x);
```

RANGE mode and PARTITION BY without ORDER BY hang as well.
The following return correctly:
- the same queries with ORDER BY in the window;
- a frame ending at CURRENT ROW;
- `last_value()`, which scans backward;
- RESPECT NULLS.

## Analysis

`ignorenulls_getfuncarginframe()` (nodeWindowAgg.c) advances `abs_pos` and
calls `row_is_in_frame(winobj, abs_pos, slot, true)` for each position. If
that returns 0, the loop moves to the next position without fetching the row.
But `row_is_in_frame()` expects its caller to have checked that the row is
inside the partition. For a frame ending at UNBOUNDED FOLLOWING, it has no
end-of-frame test. With EXCLUDE GROUP or EXCLUDE TIES and `ordNumCols == 0`,
it returns 0 for every position other than the current row, including
positions past the last row of the partition. So `window_gettupleslot()`,
which would report the end of the partition, is never called, and `abs_pos`
(an `int64`) grows without limit. In a debugger on the minimal one-row query,
`abs_pos` advanced 3.4e8 → 5.2e8 → 7.0e8 over two seconds (~1.8e8/s, backend
in state R), where any valid position is 0 — confirming a genuine infinite
loop rather than slow execution.

With ORDER BY, positions after the partition fall outside the current peer
group, `row_is_in_frame()` returns 1, and `window_gettupleslot()` ends the
loop. That is why only the no-ORDER-BY case hangs.

## Proposed fix

The attached patch does two things:
- checks the partition end before calling `row_is_in_frame()`, using the same
  test `window_gettupleslot()` uses (`spool_tuples()` + `spooled_rows`);
- adds a `CHECK_FOR_INTERRUPTS()` to the loop, which can pass over many
  excluded or known-NULL rows without fetching any tuple.

It also adds four regression queries to window.sql. Results on master:
- `make check` passes 239/239 and the isolation suite 134/134;
- the new expected output matches the `array_agg(...) FILTER` results computed
  on an unpatched server;
- 24,000 randomized IGNORE NULLS queries (all frame modes and exclusions,
  checked against the same aggregate-path oracle) give no mismatches and no
  hangs.

The patch also applies cleanly to REL_19_STABLE.

```diff
--- a/src/backend/executor/nodeWindowAgg.c
+++ b/src/backend/executor/nodeWindowAgg.c
@@ -3466,6 +3466,9 @@ ignorenulls_getfuncarginframe(WindowObject winobj, int argno,
 		int			inframe;
 		int			v;
 
+		/* we may skip many rows without fetching any of them */
+		CHECK_FOR_INTERRUPTS();
+
 		/*
 		 * Check apparent out of frame case.  We need to do this because we
 		 * may not call window_gettupleslot before row_is_in_frame, which
@@ -3474,6 +3477,18 @@ ignorenulls_getfuncarginframe(WindowObject winobj, int argno,
 		if (abs_pos < 0)
 			goto out_of_frame;
 
+		/*
+		 * Likewise, stop at the end of the partition, which row_is_in_frame
+		 * expects its caller to have checked.  It cannot always detect that
+		 * itself: for a frame ending at UNBOUNDED FOLLOWING with EXCLUDE
+		 * GROUP or EXCLUDE TIES and no ORDER BY, it reports every row other
+		 * than the current one as excluded, wherever it is, so we would
+		 * never reach the end of the loop.
+		 */
+		spool_tuples(winstate, abs_pos);
+		if (abs_pos >= winstate->spooled_rows)
+			goto out_of_frame;
+
 		/* check whether row is in frame */
 		inframe = row_is_in_frame(winobj, abs_pos, slot, true);
 		if (inframe == -1)
```

## Related threads

I searched pgsql-bugs since May 2026 and pgsql-hackers since June 2026 and
found no report of this hang. The nearest threads are about other problems:

* "nodeWindowAgg.c IGNORE NULLS abs overflow" (pgsql-hackers, 2026-10-21):
  `abs(INT_MIN)` in the same function. That patch changes only the offset
  arithmetic and wouldn't fix this loop.
* BUG #19731 / #19732: EXCLUDE TIES results in the RESPECT NULLS path of
  `WinGetFuncArgInFrame()`.
