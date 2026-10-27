# AUDIT-F2 findings: PostgreSQL correctness audit (24 October 2026)

> An independent skeptical re-verification was performed after this document.
> Verdict: **CONFIRMED LOCAL BUG** (unsent). See `AUDIT-F2_FINAL_VERDICT.md`
> and `AUDIT-F2_VERIFICATION_MATRIX.md`. The re-verification corrected two
> hand-oracle encoding errors in the test matrix (not server bugs) and
> confirmed the bug on the current tips of master and REL_19_STABLE.

## 1. Executive summary

One new defect was found and taken to report-ready status.

**AUDIT-F2: `first_value()` / `nth_value()` with IGNORE NULLS never return
when the window has no ORDER BY, the frame ends at UNBOUNDED FOLLOWING (or at
a ROWS offset far beyond the partition), and the frame uses EXCLUDE GROUP or
EXCLUDE TIES.**

* **Trigger.** The backend loops in `ignorenulls_getfuncarginframe()`
  (`src/backend/executor/nodeWindowAgg.c`) and never checks for interrupts.
  A one-line, table-free SELECT that any user can run triggers it.
* **What can't stop it.** statement_timeout, `pg_cancel_backend()`,
  `pg_terminate_backend()` and `pg_ctl stop -m fast`.
* **What it blocks.** A stuck backend also never absorbs a ProcSignalBarrier,
  so `ALTER DATABASE ... SET TABLESPACE` waits behind it.
* **The only remedy.** SIGKILL, which makes the postmaster restart all sessions.
* **Expected result.** NULL (or the current row's value under EXCLUDE TIES),
  per the frame semantics. The same query with RESPECT NULLS, or computed
  through the aggregate path, returns that at once.
* **Affected:**
  - master 126976a8ff (20devel);
  - REL_19_STABLE fc189eb750;
  - a 19rc1-era build (015f4c9fc3, REL_19_RC1-76).
* **Not affected:** 18.6, which has no IGNORE NULLS. The feature is new in
  PostgreSQL 19, so the defect would ship in 19.0.
* **Root cause.** A caller breaks `row_is_in_frame()`'s documented contract
  (the caller must establish that the row is inside the partition).
* **Fix.** A 15-line change plus regression tests, in
  `AUDIT-F2_REGRESSION_TEST.patch`. Results:
  - **Tests.** Core regression 239/239 and isolation 134/134 on patched master.
  - **Oracle.** The new expected output matches an independent aggregate-path
    oracle.
  - **Fuzz.** 24,000 randomized IGNORE NULLS queries give 0 mismatches.
  - **REL_19_STABLE.** The patch applies cleanly there and core regression
    passes 239/239.
* **Duplicates.** None found within the search scope in section 8. One
  adjacent open thread ("IGNORE NULLS abs overflow", 2026-10-21) touches the
  same function but is a different defect.
* **AUDIT-F1 exclusion.** Not related. AUDIT-F1 is a planner wrong-result bug
  in the NOT IN → anti-join conversion. AUDIT-F2 is an executor
  non-termination in window frame scanning.

Nothing has been sent upstream.

## 2. Environment

| Item | Value |
|---|---|
| Host | Windows 11, WSL2 Ubuntu 24.04.4 LTS, kernel 6.18.33.2-microsoft-standard-WSL2, x86_64, 12 CPUs |
| Compiler | gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 |
| Upstream | https://github.com/postgres/postgres.git, fetched 2026-10-23 |
| master (test) | 126976a8ffcfa47f40d3df09243ebf4606001912, "Emit null-keyed hash join outer tuples immediately when feasible." (2026-10-23), version string 20devel |
| REL_19_STABLE | fc189eb75089506fbb4ef7c3765d28f49ce3cf95 (same commit, backpatched), version string 19rc1 |
| 19rc1-era build | 015f4c9fc35f91a1ab46bafab05a3686cfe09d46 (REL_19_RC1-76), install from the AUDIT-F1 audit |
| 18 reference | 18.6, team build `~/pgfuzz/install/REL_18_STABLE` (CFLAGS=-O2, no assertions) |
| Configure (test builds) | `--enable-debug --enable-cassert --enable-tap-tests=no --with-libxml --without-icu CFLAGS='-O1 -g -fno-omit-frame-pointer'` |
| Build | `make -j12 -s && make install -s` |
| Clusters | fresh `initdb -U postgres --no-locale -E UTF8 -A trust`, Unix socket only, all planner settings default |

**Isolation.**
* Everything lives under `~/audit2` in WSL. Worktrees, each created with
  `git worktree add --detach`:
  - `m` (master, unmodified);
  - `fix` (master + patch);
  - `r19` (REL_19_STABLE, unmodified);
  - `r19fix` (REL_19_STABLE + patch).
* The team trees (`~/pgfuzz/src/*`) and the AUDIT-F1 worktrees (`~/audit/src/*`)
  were not modified.
* The project folder is not a git repository. Only this report directory
  (`bughunt/audit2/`) was added to it.
* Ports:

  | Port | Cluster |
  |---|---|
  | 5480 | master, main test cluster |
  | 5481 | 18.6 |
  | 5482 | master, disposable for hang tests |
  | 5483 | REL_19_STABLE |
  | 5484 | 19rc1-era |
  | 5485 | patched master |

The binary under test was confirmed by `SELECT version()` on every cluster
(20devel / 19rc1 / 18.6) and by the install prefix in `pg_config --configure`.

**Baseline.** Unpatched master `make check`: all 239 tests passed (log
`~/audit2/logs/check-m.log`).

## 3. Areas investigated and source paths read

| Area | Paths read | Focus |
|---|---|---|
| A: planner/executor | `executor/nodeWindowAgg.c` (IGNORE NULLS paths, `row_is_in_frame`, `spool_tuples`, `window_gettupleslot`, partition reset), `utils/adt/windowfuncs.c`, `executor/nodeHashjoin.c` (commit 126976a8ff in full), `optimizer/util/clauses.c` (`find_nonnullable_*`, `find_forced_null_var`), `optimizer/prep/prepjointree.c` (commit 02119d6c87) | the newest executor and planner changes, and PG19 features with no prior audit coverage |
| B: partitioning/catalog/DDL | `utils/adt/ri_triggers.c` (RI fast path: `ri_FastPathCheck`, `ri_LockPKTuple`, `ri_check_fastpath_index`, `recheck_matched_pk_tuple`), NOT NULL constraint DDL, hash partitioning support functions | the PG19 RI fast path, NOT NULL catalog consistency, hash routing stability across versions |
| C: types/casts/I/O | new hash support functions (`hashbool`, `hashdate`, `hashxid`, `hashcid`, `timestamptz_hash`, `hashbytea`), new `oid8` type, int↔bytea casts, text and binary I/O | new types and functions in master and 19 |

To pick targets, I read the commit history since 2026-03-01 (2,311 commits;
the clone is shallow from that date), concentrating on executor, optimizer,
partitioning, catalog, nbtree and adt. I deprioritized clusters that are
already being worked on heavily: Richard Guo's planner fixes, the REPACK
series, and the RI fast-path fix series. Features since reverted (SQL/PGQ,
FOR PORTION OF, MERGE/SPLIT PARTITION, GROUP BY ALL) were excluded.

## 4. Candidate ledger

Status vocabulary as in the brief. "Code review" means the hypothesis was
refuted by reading the code path. "Tested" means it was refuted by running
queries.

| ID | Hypothesis | Method | Status | Reason |
|---|---|---|---|---|
| **F2-A1** | **IGNORE NULLS frame scan in `ignorenulls_getfuncarginframe()` misses the partition end** | fuzz, backtrace, minimal matrix, fix, regression test | **REPORT_READY** | Sections 5–8 |
| F2-A2 | IGNORE NULLS window functions return wrong values: nullness cache, `lag`/`lead` offsets and defaults, `nth_value`, every frame mode and exclusion, spill to disk | differential fuzz, oracle = `array_agg(e) FILTER (WHERE e IS NOT NULL) OVER w`: 24,000 queries on patched master (seeds 10–17 × 3,000) | REJECTED (tested) | 0 mismatches, 0 errors. The same seeds on unpatched master hung at once (F2-A1), so they could only be completed on the patched build. The patch changes only loop termination, not which in-partition rows count. |
| F2-A3 | Commit 126976a8ff (master tip, null-keyed hash join outer tuples emitted at once) loses or duplicates rows | code review + tested (`probes/a_hj_null.sql`): LEFT/FULL/RIGHT/anti/right-anti/semi, extra join qual, LATERAL and correlated rescans × {1 batch, 16 batches, parallel-aware 1/multi batch, parallel-oblivious}, against `enable_hashjoin = off` | REJECTED (tested) | 45 comparisons, 0 differences. The plan confirmed a 16-batch Hash Full Join. |
| F2-A4 | Whole-row `b IS NULL` → anti-join reduction (02119d6c87) is wrong when a matched row has all columns NULL, or when the proof comes from a record comparison | code review (`prepjointree.c` `forced_null_var_is_nonnullable`, `forced_null_var_is_attnotnull`) | REJECTED (code review) | A proof on the whole-row attribute is discarded explicitly. Only a real user column proven non-null counts, and system columns are excluded. |
| F2-A5 | Row-format `IS NOT NULL` strictness (f863be3e2d) is fooled by a nested `ROW(...)` field, which is non-null even when its fields are NULL | code review (`clauses.c` walkers) | REJECTED (code review) | Neither walker descends into `RowExpr`, so `ROW(..., ROW(b.y)) IS NOT NULL` proves nothing about `b`. |
| F2-A6 | Join/aggregate planning on new master disagrees with 18.6 (team fuzzer `joinfuzz2`, run against master 126976a8ff) | cross-version differential fuzz, random planner settings | REJECTED (tested, partial) | Checkpoint at 4,000 of 6,000 planned: 3,872 queries, 0 mismatches, 0 crashes, 0 one-side errors, 128 timeouts. The run was not finished when this report was written. |
| F2-B1 | RI fast path (`ri_FastPathCheck`) reports a violation, or misses one, where the SPI path would not | code review: one index probe vs. the SPI scan, TM_* handling, snapshot timing, coercion and collation eligibility | REJECTED (code review only) | A unique non-deferrable index has at most one visible match per key, and TM_Deleted/TM_SelfModified/traversed handling matches `ExecLockRows`. Concurrency was **not** tested; others are actively fixing this area. |
| F2-B2 | DDL sequences (inheritance, partitions, ATTACH/DETACH, SET/DROP NOT NULL, NOT VALID, NO INHERIT, ALTER CONSTRAINT [NO] INHERIT, PK/UNIQUE, ALTER TYPE, DROP/ADD COLUMN, savepoints) leave NULLs under a validated NOT NULL, or make the planner's NOT NULL folding give wrong counts | DDL-sequence fuzzer `nnfuzz.py`. Invariants: I1 (no NULL under a validated NOT NULL), I2 (`IS NULL` count vs `num_nulls()`), I3 (LEFT JOIN … IS NULL vs `num_nulls()`), after every statement | REJECTED (tested) | 6 seeds × 60 episodes on master 126976a8ff: 14,253 statements accepted and 3,395 rejected by the server (expected for random DDL). Invariants checked after every step for every table (with and without ONLY) and column: 0 violations, 0 internal errors. |
| F2-B3 | The new dedicated hash support functions change hash values, so hash-partitioned tables carried over by pg_upgrade would route rows differently | tested (`probes/hashroute.sql`): 85 values of 33 hashable types routed into 7 hash partitions on 18.6 and on master | REJECTED (tested) | Routing identical (`diff` empty). `money`, `bit` and `varbit` have no hash opclass on either version. |
| F2-C1 | New `oid8` type: input, wraparound, unsigned ordering, casts | probe (`probes/c_oid8.sql`) | REJECTED (tested) | Consistent with the `oid` precedent: `-1` wraps, int8→oid8 is a binary cast, ordering is unsigned, out-of-range input is rejected softly. |
| F2-C2 | New int2/int4/int8 ↔ bytea casts break at the boundaries | probe (`probes/c_casts.sql`) | REJECTED (tested) | Round trips are exact at 0, ±1 and the extremes. Over-long input raises "integer out of range". |
| F2-C3 | Text or binary I/O round trip fails for a stored value | `rtcheck.py` over every user column of the regression database: text in/out, then binary recv(send) compared by text and by bytes | REJECTED (tested, partial coverage) | 247 columns, 10,159 distinct values, 0 failures. 29 columns skipped (no equality operator for DISTINCT). The regression DB was only partly built, because installcheck was interrupted when the cluster had to be restarted because of F2-A1. |

AUDIT-F1-area hypotheses (NOT IN / anti-join casts) were deliberately not
re-tested. The prior audit's negative results (partition pruning, btree vs
seqscan, hash opclass invariants, JSON_TABLE, #19735, #19746) were not
repeated.

## 5. Confirmed defect: reproduction and expected vs. actual behavior

**How it was found.** The IGNORE NULLS fuzzer (`fuzz/winfuzz.py`) was started
with 8 seeds. All 8 sessions stopped making progress. `pg_stat_activity`
showed them `active` with no wait event for 8+ minutes. A concurrent
installcheck was stuck in `ALTER DATABASE regression_utf8 SET TABLESPACE`,
waiting on `IPC / ProcSignalBarrier`. A gdb backtrace (taken twice, one second
apart) showed:

```
#0 row_is_in_frame (..., pos=45027289153, ..., fetch_tuple=true) at nodeWindowAgg.c:1606
#1 ignorenulls_getfuncarginframe (..., relpos=-1, argno=0, ...) at nodeWindowAgg.c:3478
#2 WinGetFuncArgInFrame (..., relpos=1, seektype=1, set_mark=true, ...) at nodeWindowAgg.c:4042
#3 window_nth_value (...) at windowfuncs.c:719
...
#0 row_is_in_frame (..., pos=45073218109, ...)
```

The table had at most 400 rows, yet `pos` was about 4.5e10 and rising. The
query was
`nth_value(nullif(x, o), 2) IGNORE NULLS OVER (ROWS BETWEEN 2 FOLLOWING AND UNBOUNDED FOLLOWING EXCLUDE GROUP)`.

**Minimal reproducer** (`AUDIT-F2_REPRODUCER.sql`):

```sql
SELECT first_value(x) IGNORE NULLS OVER w
FROM (VALUES (1)) v(x)
WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP);
```

**Expected.** One row, NULL.
* SQL frame semantics, from the PostgreSQL docs (`syntax.sgml`, section 4.2.8):
  - Without a window ORDER BY, "all rows become peers of the current row".
  - "EXCLUDE GROUP excludes the current row and its ordering peers from the
    frame."

  So the frame is empty, and `first_value()` over an empty frame is NULL.
* Control 1. The same query without IGNORE NULLS returns NULL at once.
* Control 2. The same frame through the aggregate path,
  `(array_agg(x) FILTER (WHERE x IS NOT NULL) OVER w)[1]`, returns NULL at once.

**Actual.** The statement never completes. Under the watchdog harness
(`hang.sh`) with `statement_timeout = 2s`, `pg_stat_activity` showed
`active`, no wait event, 8 s elapsed. The backend was still `active` after
`pg_cancel_backend()` and again after `pg_terminate_backend()`, with
13–16 s of CPU time (process state `R`).

**Minimal matrix** (`probes/wf_min.sh`, master 126976a8ff; each case run on
the disposable cluster with an 8 s watchdog):

| Case | Window | Result (unpatched) | Result (patched) |
|---|---|---|---|
| t1 | `first_value` IGNORE NULLS, ROWS UNBOUNDED…UNBOUNDED, EXCLUDE GROUP, 1 row | **HANG** | NULL |
| c2 | same, RESPECT NULLS | NULL | NULL |
| c3 | same, with ORDER BY | NULL | NULL |
| c4 | aggregate-path oracle | NULL | NULL |
| t5 | `first_value` IGNORE NULLS, EXCLUDE TIES, rows (NULL),(2) | **HANG** | (NULL→NULL), (2→2) |
| c6 | same, rows (1),(2) (value found before the end) | 1, 2 | 1, 2 |
| t7 | `nth_value(x,2)` IGNORE NULLS, CURRENT ROW…UNBOUNDED, EXCLUDE TIES | **HANG** | NULL, NULL |
| t8 | RANGE UNBOUNDED…UNBOUNDED, EXCLUDE GROUP | **HANG** | NULL |
| c9 | frame ending at CURRENT ROW, EXCLUDE GROUP | NULL | NULL |
| c10 | `last_value` (scans backward) | NULL | NULL |
| c11 | empty input | 0 rows | 0 rows |
| t12 | PARTITION BY x, no ORDER BY, EXCLUDE GROUP | **HANG** | NULL, NULL |
| t13 | ROWS … AND 1000000000000 FOLLOWING, EXCLUDE GROUP | **HANG** (the scan walks ~1e12 positions with no interrupt check) | NULL |
| c14 | ROWS … AND 1000 FOLLOWING, EXCLUDE GROUP | NULL (scans ≤ 1,000 positions, then `row_is_in_frame()` returns -1) | NULL |

The patched results equal the RESPECT NULLS and aggregate-path controls and
the values derived by hand from the frame definitions.

**Operational impact (demonstrated).**
* statement_timeout ineffective: the 2 s and 5 s timeouts never fired.
* `pg_cancel_backend()` and `pg_terminate_backend()` ineffective (still
  `active` after 10 s each).
* `pg_ctl stop -m fast -t 30` failed: "server does not shut down", exit 1.
  The backend was still running.
* Barrier waiters blocked: `ALTER DATABASE ... SET TABLESPACE` waited on
  ProcSignalBarrier while the looping backends ran.
* Recovery requires `kill -9` on the backend, which makes the postmaster
  terminate every session and run crash recovery.
* No special privilege is needed: any role that can run a SELECT can trigger
  it, without any table.

## 6. Root-cause analysis

Paths in `src/backend/executor/nodeWindowAgg.c` at 126976a8ff. Line numbers
are for the unpatched file.

1. `window_first_value()` and `window_nth_value()` (`utils/adt/windowfuncs.c`
   lines 663, 719) call
   `WinGetFuncArgInFrame(winobj, 0, relpos, WINDOW_SEEK_HEAD, ...)`. With
   IGNORE NULLS, `WinGetFuncArgInFrame()` (line 4041) hands off to
   `ignorenulls_getfuncarginframe()`.
2. `ignorenulls_getfuncarginframe()` (lines 3407–3537) starts at
   `frameheadpos` and walks forward (`forward = 1`) until it has seen
   `relpos + 1` non-null values. Each iteration does the following:
   * rejects `abs_pos < 0` (lines 3474–3475);
   * calls `row_is_in_frame(winobj, abs_pos, slot, true)` (line 3478);
   * on 0, jumps to `advance` without touching the row (lines 3481–3482);
   * calls `window_gettupleslot()` only for an in-frame row whose nullness is
     not cached (line 3493) or for the final target (line 3513).
3. `row_is_in_frame()` (lines 1503–1606) requires, per its header comment,
   that "the caller must have already determined that the row is in the
   partition". Its frame-end checks exist only for
   `FRAMEOPTION_END_CURRENT_ROW` and `FRAMEOPTION_END_OFFSET`. A frame ending
   at UNBOUNDED FOLLOWING has none. Its exclusion check (lines 1586–1601)
   returns 0 unconditionally when `node->ordNumCols == 0` (all rows are
   peers) for EXCLUDE GROUP, and for EXCLUDE TIES whenever
   `pos != currentpos`. A ROWS end offset whose addition to `currentpos`
   does not overflow gives a -1 only at `currentpos + offset`. For an offset
   such as 1000000000000 that is far beyond the partition, and since
   8b6c89e377 an overflowing offset counts as "to the end of the partition".
4. So once `abs_pos` passes the last row, every call returns 0. The loop
   never calls `window_gettupleslot()`, the only place that would see
   `pos >= spooled_rows` and report the end of the partition, and it advances
   until `abs_pos` overflows (about 9.2e18 iterations).
   Neither `row_is_in_frame()` nor the loop calls `CHECK_FOR_INTERRUPTS()`.
   `window_gettupleslot()` does (line 3290), but it is never reached. So no
   interrupt (cancel, timeout, terminate, barrier) is processed.
5. Why other shapes terminate:
   * **With ORDER BY:** a position after the partition is not in the current
     peer group, `row_is_in_frame()` returns 1, and `window_gettupleslot()`
     then fails, giving `out_of_frame`.
   * **With a bounded frame end:** `row_is_in_frame()` returns -1.
   * **`last_value()`:** scans backward, and the loop stops at `abs_pos < 0`.
   * **RESPECT NULLS:** `WinGetFuncArgInFrame()` fetches the target row before
     calling `row_is_in_frame()` (lines 4045ff), as the contract requires.
   * **`lag`/`lead` IGNORE NULLS** (`WinGetFuncArgInPartition`): calls
     `gettuple_eval_partition()` for every uncached row, which detects the
     partition end.

**Fix (minimal).** Before calling `row_is_in_frame()`, establish partition
membership the way `window_gettupleslot()` does:
`spool_tuples(winstate, abs_pos); if (abs_pos >= winstate->spooled_rows) goto out_of_frame;`.
Also add `CHECK_FOR_INTERRUPTS()` at the top of the loop.

Why this doesn't break nearby cases:
* `spool_tuples()` is the same call `window_gettupleslot()` and the
  `fetch_tuple` path of `row_is_in_frame()` would make. It has no effect when
  the partition is already spooled, and it handles pass-through mode and
  spilled tuplestores itself.
* Rows inside the partition are treated exactly as before, so results for
  every terminating case are unchanged. Evidence:
  - all existing window tests pass;
  - the 24,000-query fuzz gives 0 mismatches;
  - the nullness cache never receives an out-of-partition position.

**Introduced by:** the IGNORE NULLS feature of PostgreSQL 19. Per the
feature thread its author is Tatsuo Ishii; it was committed before
2026-03-01, where the local shallow history begins. `git blame` attributes
all 73 lines of the loop (lines 3464–3536) to that history boundary, so none
were changed afterwards. Later commits touching nodeWindowAgg.c:
* 26269fe3c8 (nullness cache for volatile arguments) touched only the cache;
* d451ca6917 (window function dedup) did not touch the loop;
* 8b6c89e377 (integer overflow in frame offsets) changed `row_is_in_frame()`'s
  ROWS end-offset test, not the loop.

## 7. Version scope, tests, and campaign results

| Build | Commit | t1 / t5 | Control (RESPECT NULLS) |
|---|---|---|---|
| master 20devel | 126976a8ff | HANG / HANG | NULL |
| REL_19_STABLE | fc189eb750 | HANG / HANG | NULL |
| 19rc1-era | 015f4c9fc3 (REL_19_RC1-76) | HANG / HANG | NULL |
| 18.6 | REL_18_STABLE build | syntax error at "NULLS" (feature absent) | NULL |
| master + patch | 126976a8ff + fix | NULL / (NULL, 2) | NULL |

Test suites:

| Build | Core regression (`make check`) | Isolation |
|---|---|---|
| master, unpatched (baseline) | 239/239 | not run |
| master + patch | 239/239 | 134/134 |
| REL_19_STABLE + patch | 239/239 | not run |
| new `window` tests on the unpatched server | never finish (pg_regress killed by a 180 s watchdog, exit 124) | |

Exact commands and outputs are in `AUDIT-F2_TEST_RESULTS.md`.

## 8. Duplicate screening

| Source | Scope | Search | Result |
|---|---|---|---|
| postgresql.org site search (all lists) | relevance-ranked; the date filter was ignored by the site | `IGNORE NULLS`, `ignorenulls_getfuncarginframe`, `row_is_in_frame`, `IGNORE NULLS EXCLUDE GROUP`, `IGNORE NULLS EXCLUDE TIES`, `first_value IGNORE NULLS`, `nth_value IGNORE NULLS`, `IGNORE NULLS infinite loop`, `IGNORE NULLS hang`, `window function infinite loop`, `window function cannot cancel`, `EXCLUDE GROUP without ORDER BY`, `null treatment window`, `notnull_info`, `RESPECT NULLS` | Only the original feature thread ("Add RESPECT/IGNORE NULLS and FROM FIRST/LAST options", 2018–2025), the committed fix "Fix multi WinGetFuncArgInFrame/Partition calls with IGNORE NULLS", and unrelated hits. No report of a hang or loop. |
| pgsql-bugs list pages | every message 2026-05-01 → 2026-10-24 (2,250 messages, then a per-day pass from 2026-09-15) | subjects matching ignore/respect nulls, null treatment, nth/first/last_value, exclude group/ties, window func/agg, WindowAgg, infinite loop, uncancel, statement_timeout | Window-related reports: #19532, #19533 (run-condition pushdown), #19713 (qual pushdown), #19731, #19732 (EXCLUDE TIES, RESPECT NULLS path), JSON_ARRAYAGG EXPLAIN, #19692 (pruning delays statement_timeout). None involves IGNORE NULLS or a window-function hang. |
| pgsql-hackers list pages | 2026-06-01 → ~2026-09 (12,000 messages), plus a per-day pass 2026-09-15 → 2026-10-24 (4,646 distinct messages across both lists) | same patterns | IGNORE NULLS threads: "IGNORE/RESPECT NULLS can be specified for (prokind == 'f')" (June; fixed by 4e5920e6de/419ce13b70), "Fix duplicate detection for null-treatment window functions" (July; d451ca6917), **"nodeWindowAgg.c IGNORE NULLS abs overflow"** (2026-10-21, open; author reply 2026-10-22 says it will be handled after November 4). |
| #19731 and #19732 threads | read in full | — | About the RESPECT NULLS offset adjustment in `WinGetFuncArgInFrame()`. No mention of IGNORE NULLS, loops or hangs. |
| git history | master and REL_19_STABLE, 2026-03-01 → 126976a8ff / fc189eb750 | `-S ignorenulls_getfuncarginframe`; `--grep` null treatment / IGNORE NULLS; `git log` on nodeWindowAgg.c and windowfuncs.c | No commit changes the loop's end condition. |
| regression tests | `src/test/regress/sql/window.sql` at 126976a8ff | IGNORE NULLS lines (41) combined with EXCLUDE | **0**: no existing test covers IGNORE NULLS with an exclusion clause. |

**The nearest open item.** "IGNORE NULLS abs overflow"
(CACJufxH2_4ucJ58_YQPin8E8hf2RRD6S7rA-UK9pSWxdg7YBQw@mail.gmail.com) reports
that `abs(relpos)` overflows for `lead(v, -2147483648) IGNORE NULLS`. Its
patch changes only `notnull_offset`/`notnull_relpos` to int64 with
`pg_abs_s32()`. It doesn't touch the loop's end condition. AUDIT-F2
reproduces with relpos 0 or 1, where there is no overflow. So it is a
different defect in the same function, and the two patches touch different
hunks.

**Conclusion.** No duplicate was found **within the scope above**. That is
not a claim that nobody else knows about it.

**Uncertainty.**
* The site search ranks by relevance and doesn't honor its date filter.
* The pgsql-hackers pass for June to mid-September stopped at a 12,000-message
  cap, likely short of mid-September. The per-day pass covers Sept 15 onward.
* The commitfest application and pgsql-committers were not checked
  separately (git history stands in for committers).
* Private reports to security@postgresql.org can't be seen.

## 9. Limitations

* **Concurrency.** RI fast path and REPACK were not tested under concurrency
  (F2-B1 is code review only).
* **No ICU.** Built `--without-icu`, so nondeterministic collations were not
  exercised.
* **TAP tests.** Not run in the initial pass (`--enable-tap-tests=no`); run in
  the follow-up verification pass on the patched build and passing (see
  `AUDIT-F2_TEST_RESULTS.md` §0 and `AUDIT-F2_FINAL_VERDICT.md` §9).
* **I/O coverage.** F2-C3 (I/O round trip) covered only the part of the
  regression database that existed when installcheck was interrupted.
* **Fuzz scope.** "Rejected (tested)" for fuzz campaigns means no
  counterexample in the generated space, not proof of correctness.
* **Not upstream-approved.** The proposed patch is not upstream-reviewed.
  `CHECK_FOR_INTERRUPTS()` is defense in depth: the partition-end check alone
  ends the loop. A committer might prefer to fix `row_is_in_frame()` instead,
  or as well.
