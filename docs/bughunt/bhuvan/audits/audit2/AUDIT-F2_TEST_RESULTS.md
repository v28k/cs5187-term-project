# AUDIT-F2 test results

All commands ran in WSL2 Ubuntu 24.04 as user `bhuvi`, invoked from PowerShell
as `wsl -u bhuvi -- bash /home/bhuvi/audit2/<script>`. The scripts are copied
under `scripts/` here; inside WSL they live in `~/audit2/`. Logs are in
`~/audit2/logs/`.

## 0. Status key (verified / partial / unrun)

Updated during the final verification pass (see `AUDIT-F2_FINAL_VERDICT.md`
and `AUDIT-F2_VERIFICATION_MATRIX.md`).

| Check | Status | Count / outcome |
|---|---|---|
| Core regression, unpatched master (baseline) | VERIFIED | 239/239 (`check-m.log`) |
| Core regression, patched master | VERIFIED | 239/239 (`check-fix-final2.log`) |
| Core regression, patched REL_19_STABLE | VERIFIED | 239/239 (`check-r19fix.log`) |
| Isolation, patched master | VERIFIED | 134/134 (`isolation-fix.log`) |
| New window tests on unpatched server (must hang) | VERIFIED | pg_regress killed by 180 s watchdog, exit 124 |
| Bounded causal matrix, unpatched + patched | VERIFIED | 6 timeouts unpatched / 0 patched; 0 oracle mismatch (matrix JSON) |
| last_value IGNORE NULLS + EXCLUDE TIES + no ORDER BY (contributor follow-up) | VERIFIED | master 239/239, REL_19_STABLE 239/239; hand-derived + aggregate-oracle match |
| Debugger nontermination evidence | VERIFIED | `pos` advances ~1.8e8/s, state R (`backtrace.txt`) |
| IGNORE NULLS fuzz vs oracle, patched | VERIFIED | 8×3000 = 24,000, 0 mismatches |
| hash-join null-key differential | VERIFIED | 45 comparisons, 0 differences |
| NOT NULL DDL fuzz | VERIFIED | 6×60 episodes, 0 violations |
| hash-partition routing 18 vs master | VERIFIED | identical, 85 values |
| text/binary I/O round trip | PARTIAL | 247 columns, 10,159 values, 0 failures, 29 skipped (no equality op); DB partial — installcheck interrupted by the hang (re-verified 2026-10-25) |
| joinfuzz2 master vs 18.6 | VERIFIED (complete) | seed 901: 5,829 queries, 0 mismatch, 0 crash, 0 one-side error, 171 timeouts |
| Isolation, unpatched master / patched REL_19 | UNRUN | not needed for a single-backend hang |
| TAP: psql suite (patched, TAP build) | VERIFIED | 5 files, 253 tests, PASS — incl. `020_cancel` (SIGINT cancels a running query) and `099_audit_f2` (23 AUDIT-F2 assertions) |
| TAP: test_misc (patched) | VERIFIED | 15 files, 168 tests, PASS |
| TAP: pg_ctl (patched) | VERIFIED | 4 files, 54 tests, PASS |

### TAP tests (added in the follow-up pass)

`IPC::Run` 20260402.0 (plus IO::Tty) was installed into `~/perl5` without root
(`scripts/verify/install_ipcrun.sh`); the patched worktree was rebuilt with
`--enable-tap-tests` into `install/fixtap` (`scripts/verify/tap_build.sh`,
same patched source). With `PERL5LIB=~/perl5/lib/perl5`:

```
t/001_basic.pl ........... ok
t/010_tab_completion.pl .. ok
t/020_cancel.pl .......... ok      # SIGINT cancels a running query
t/030_pager.pl ........... ok
t/099_audit_f2.pl ........ ok      # 23 assertions, see below
All tests successful. Files=5, Tests=253.  Result: PASS   (src/bin/psql)

test_misc:  All tests successful. Files=15, Tests=168.  Result: PASS
pg_ctl:     All tests successful. Files=4,  Tests=54.   Result: PASS
```

`099_audit_f2.pl` (`scripts/verify/099_audit_f2.pl`, an untracked test, not
part of the proposed patch) asserts, on the patched build, that the six
queries that loop forever on unpatched 19/master each (a) complete with rc=0,
(b) return the expected value, and (c) raise no error/timeout — then confirms
SIGINT cancels a running query on the same node. 23 assertions, all pass.
A first run failed because that test's own SIGINT block started psql without
the node's environment (a bug in the test, not the server); `020_cancel.pl`
passed throughout, and the corrected `099` passes 23/23. Logs:
`tap_psql_all.log`, `tap_099.log`, and `scripts/verify/evidence/tap*.txt`.

Note: these TAP suites are the ones relevant to the affected path
(query cancellation / interrupts, misc server behaviour, start/stop). There is
no upstream TAP test dedicated to window functions; window correctness is
covered by `window.sql` (run above, 239/239). TAP was run only on the patched
build; the unpatched reproducer is not suitable as an unmodified TAP case
because it would hang the harness (the `099` assertions are gated to the
patched build and bounded by `statement_timeout`).

## 1. Builds

| Build | Worktree | Commit | Script |
|---|---|---|---|
| `m` (master, unpatched) | `~/audit2/src/m` | 126976a8ffcfa47f40d3df09243ebf4606001912 | `setup.sh` |
| `r19` (REL_19_STABLE, unpatched) | `~/audit2/src/r19` | fc189eb75089506fbb4ef7c3765d28f49ce3cf95 | `build19.sh` |
| `fix` (master + patch) | `~/audit2/src/fix` | 126976a8ff + `AUDIT-F2_REGRESSION_TEST.patch` | `buildfix.sh` |
| `r19fix` (REL_19_STABLE + patch) | `~/audit2/src/r19fix` | fc189eb750 + same patch | `r19fix.sh` |
| `r19rc1` | `~/audit/src/pg-19` (AUDIT-F1) | 015f4c9fc3 (REL_19_RC1-76) | existing install |
| `r18` | `~/pgfuzz/src/postgres-REL_18_STABLE` | 18.6 (d7938ff) | existing team install |

Configure (all four new builds):

```
./configure --prefix=$HOME/audit2/install/<build> --enable-debug --enable-cassert \
  --enable-tap-tests=no --with-libxml --without-icu CFLAGS='-O1 -g -fno-omit-frame-pointer'
make -j12 -s && make install -s
```

The patched build compiled with no compiler warnings (`grep -i warning
make-fix.log`: none).

Clusters: `cluster.sh <build> <port> start [datadir]`, which runs `initdb -U
postgres --no-locale -E UTF8 -A trust` and listens only on the Unix socket in
`/tmp`.

## 2. Baseline (before any change)

```
cd ~/audit2/src/m && make check        # baseline.sh
# All 239 tests passed.                 exit=0
```

## 3. Reproduction on affected and unaffected versions

The harness `hang.sh <build> <port> <label> <sqlfile> <seconds>` works like this:
1. runs the file with `PGOPTIONS='-c statement_timeout=2s'`;
2. if the client is still running after `<seconds>`, prints `pg_stat_activity`
   for the backend;
3. calls `pg_cancel_backend()`, waits 3 s, then `pg_terminate_backend()`,
   waits 3 s, and prints the state again;
4. sends SIGKILL and waits for crash recovery.

Matrix: `probes/wf_min.sh <build> <port>`. Version scope: `scope.sh`.

### master 126976a8ff, unpatched (port 5482)

```
[m t1_min] HANG: still running after 8s despite statement_timeout=2s (backend 18589)
active|||8
after cancel+terminate: active
  18589 Rs   00:00:13
[m c2_respect] FINISHED in <= 1s:      first_value = (null), 1 row
[m c3_orderby] FINISHED in <= 1s:      first_value = (null), 1 row
[m c4_oracle] FINISHED in <= 1s:       array_agg   = (null), 1 row
[m t5_ties] HANG ... after cancel+terminate: active   (20096 Rs 00:00:13)
[m c6_ties_found] FINISHED in <= 1s:   (1,1) (2,2)
[m t7_nth] HANG ... after cancel+terminate: active    (20931 Rs 00:00:12)
[m t8_range] HANG ... after cancel+terminate: active  (21753 Rs 00:00:13)
[m c9_currow] FINISHED in <= 1s:       (null)
[m c10_last] FINISHED in <= 1s:        (null)
[m c11_empty] FINISHED in <= 1s:       0 rows
[m t12_part] HANG ... after cancel+terminate: active  (22785 Rs 00:00:13)
[m t13_bigoff] HANG ... after cancel+terminate: active (51076 Rs 00:00:10)
[m c14_smalloff] FINISHED in <= 1s:    (null)
```

### REL_19_STABLE fc189eb750 (port 5483) and 19rc1-era 015f4c9fc3 (port 5484)

```
[r19 t1_min] HANG ... after cancel+terminate: active   (25169 Rs 00:00:14)
[r19 t5_ties] HANG ... after cancel+terminate: active  (25215 Rs 00:00:14)
[r19 c2_respect] FINISHED in <= 1s: (null)
[r19rc1 t1_min] HANG ... after cancel+terminate: active  (25266 Rs 00:00:14)
[r19rc1 t5_ties] HANG ... after cancel+terminate: active (25310 Rs 00:00:14)
[r19rc1 c2_respect] FINISHED in <= 1s: (null)
```

Version note (clarified during verification): `fc189eb750` (built as `r19`) is
an ancestor of the current `REL_19_STABLE` tip. The commit built as the
"19rc1-era" install, `015f4c9fc3`, **is** the current `origin/REL_19_STABLE`
tip (checked with `git fetch`; no commit touches `nodeWindowAgg.c` between
`fc189eb750` and it). So the hang is confirmed on the live tip of the stable
branch, not only on an older point.

### 18.6 (port 5481): not affected, feature absent

```
[r18 t1_min] FINISHED in <= 1s:
ERROR:  syntax error at or near "NULLS"
[r18 c2_respect] FINISHED in <= 1s: (null)
```

### The reproducer file itself (`AUDIT-F2_REPRODUCER.sql`)

On master (5482): control 1 and control 2 return `(null)`, then `SET`, then
the IGNORE NULLS query hangs and outlasts cancel and terminate. The
"connection lost" that follows is the harness's SIGKILL. On patched master
(5485), all three queries return `(null)` at once.

### Operational impact

`shutdown_demo.sh`, on the disposable master cluster:

```
pg_ctl -D ... -m fast -t 30 -w stop
waiting for server to shut down................................. failed
pg_ctl: server does not shut down
pg_ctl exit code: 1
  42377 Rs   00:00:33 postgres: postgres postgres [local] SELECT
```

Observed during the fuzz campaign (`activity.sh`): eight looping backends
(`active`, no wait event, 8+ min), and `ALTER DATABASE regression_utf8 SET
TABLESPACE regress_tblspace` from installcheck waiting on
`IPC / ProcSignalBarrier`.

`cancel_test.sh 12146`, against a backend that had been looping for 10
minutes:

```
before: 12146|active|00:10:16
10s after pg_cancel_backend:    12146|active|00:10:26
10s after pg_terminate_backend: 12146|active|00:10:37
  12146 Rs  10:40 00:09:41 postgres: postgres wf_10 [local] SELECT
```

Backtrace (`gdb -p` as root, two samples one second apart): `row_is_in_frame
(pos=45027289153)` ← `ignorenulls_getfuncarginframe` ← `WinGetFuncArgInFrame` ←
`window_nth_value`, then `pos=45073218109`.

## 4. Regression test: before vs. after the fix

### Before the fix: the new test never finishes

`pre_fix_regress.sh` runs the patched `window.sql`/`window.out` against the
unpatched master server (existing `regression` database, port 5480) under a
180 s watchdog:

```
timeout 180 ./pg_regress --use-existing --dbname=regression --host=/tmp --port=5480 \
  --user=postgres --bindir=$HOME/audit2/install/m/bin --inputdir=$REG --outputdir=$OUT window
pg_regress exit code: 124  (124 = killed by 180 s watchdog)
40488|active|179|SELECT x, first_value(x) IGNORE NULLS OVER w, nth_value(x, 2) IGNORE NULLS OVER w FROM (VALUES (1), (NULL), (3)) v(x) WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECED...
```

`results/window.out` ends right after echoing the first new query; no result
was ever produced.

### After the fix: master + patch

```
cd ~/audit2/src/fix && make check            # checkfix.sh fix fix-final2
# All 239 tests passed.                       exit=0
```

```
make -C src/test/isolation check             # post_fix_extra.sh
# All 134 tests passed.                       exit=0
```

### After the fix: REL_19_STABLE + patch

```
cd ~/audit2/src/r19fix && git apply ~/audit2/report/fix.diff   # r19fix.sh; then configure, make
make check
# All 239 tests passed.                       exit=0
```

### Independent check of the new expected output

The expected output was not just copied from the patched run.
`probes/oracle_newtests.sql` computes the same three original queries on the
**unpatched** server through the aggregate path
(`(array_agg(x) FILTER (WHERE x IS NOT NULL) OVER w)[n]`), which doesn't use
the buggy function. Its output is identical, row for row, to the patched
`results/window.out`:

```
 x | first_value | nth_value        x | first_value | nth_value        p | x | first_value
 1 |             |                  1 |           1 |                  1 | 1 |           1
 3 |             |                  3 |           3 |                  1 |   |
   |             |                    |             |                  2 |   |
```

The change to `expected/window.out` is a pure insertion of 56 lines; no
existing line is removed or changed.

### Contributor follow-up: last_value IGNORE NULLS with EXCLUDE TIES and no ORDER BY

A PostgreSQL contributor reviewed the patch and asked for one more test:

> Could you add last_value IGNORE NULLS with EXCLUDE TIES and no ORDER BY?
> It scans backward, so it would catch a later fix in row_is_in_frame that
> returns -1 for every position after the current row.

That query is now the fourth AUDIT-F2 test:

```sql
SELECT x,
       last_value(x) IGNORE NULLS OVER w
FROM (VALUES (1), (2), (3)) v(x)
WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE TIES)
ORDER BY x;
```

With EXCLUDE TIES and no ORDER BY, every row is a peer of the current row and
EXCLUDE TIES removes all peers except the current row, so the frame holds only
the current row; last_value() therefore returns each row's own value:

```
 x | last_value
---+------------
 1 |          1
 2 |          2
 3 |          3
(3 rows)
```

This query does not trigger the original bug (the backward scan always
terminates, even unpatched).  Its purpose is to guard the backward-scan path:
last_value() starts at the frame tail, which is a row *after* the current row
for every row except the last.  If a later fix made row_is_in_frame() return
-1 for every position after the current row (a plausible optimisation for the
forward scan), the backward scan would stop at that -1 and return NULL instead
of the current row's value.  The result was checked by hand, against the
aggregate-path oracle, and on the patched build; all agree.  The unpatched
build returns the same values for this query, confirming it is a regression
guard rather than a reproducer.

Results:
- master + patch: `make check` 239/239 (`/tmp/f2_full_check3.log`).
- REL_19_STABLE + patch: `make check` 239/239 (`/tmp/f2_r19_check.log`).

## 5. Differential fuzzing

| Campaign | Build | Size | Result |
|---|---|---|---|
| `winfuzz.py` IGNORE NULLS vs. aggregate-path oracle (seeds 10–17) | master, unpatched | 8 × 3,000 planned | all 8 sessions hung within minutes (this is how F2 was found); no mismatch was printed before they hung |
| same seeds | master + patch | 8 × 3,000 = 24,000 queries | `mismatches=0 distinct_errors=0` for every seed, no hangs |
| `a_hj_null.sql` hash join with null keys (126976a8ff) | master, unpatched | 9 queries × 5 configurations vs. `enable_hashjoin=off` | 45 comparisons, 0 differences (the plan showed 16 batches) |
| `nnfuzz.py` NOT NULL DDL sequences | master, unpatched | 6 seeds × 60 episodes; 14,253 statements accepted and 3,395 rejected by the server | 0 invariant violations, 0 internal errors |
| `joinfuzz2` (team fuzzer) master vs 18.6 | master, unpatched | 6,000 planned; **completed** (5,829 queries) | 4,816 equal, 1,003 errors on both sides, **0 mismatches, 0 crashes, 0 one-side errors**, 171 timeouts. Final summary `{"done": true, "seed": 901, ...}` in `~/audit2/jf/run_901.log`; `~/audit2/jf/out/` empty (no mismatch files). |
| `hashroute.sql` hash partition routing 18.6 vs master | both | 85 values, 33 types | identical |
| `rtcheck.py` text/binary round trip | master, unpatched | 247 columns, 10,159 values | 0 failures (29 columns skipped: no equality operator) |

## 6. Remaining limitations / not-run items

* **Isolation suite** was run only on patched master (134/134). It was not run
  on unpatched master or on REL_19_STABLE + patch; the hang is single-backend
  and does not need one.
* **TAP suites** were run only on the patched build (see §0). They are not
  evidence about the unpatched build, which would hang the harness.
* **Differential fuzzers** (`winfuzz`, `joinfuzz2`, `nnfuzz`, `hashroute`) were
  run on the unpatched master and/or patched builds as tabulated in §5; none
  was re-run for the test-only follow-up, because the C fix is unchanged.
* **Follow-up test coverage.** The `last_value()` follow-up test was verified
  only by the core regression suite (239/239) on patched master and patched
  REL_19_STABLE on 2026-10-25; it was not re-run through the TAP, isolation or
  fuzz campaigns.

## 7. How another developer can reproduce

1. Build any PostgreSQL 19 or master tree (before this fix) and start a
   **disposable** cluster.
2. Run `psql -X -f AUDIT-F2_REPRODUCER.sql`. Two controls print `(null)`; the
   third statement never returns. In another session, `pg_stat_activity`
   shows it `active` with no wait event, and `pg_cancel_backend()` /
   `pg_terminate_backend()` don't end it. Stop it with `kill -9 <pid>` (the
   postmaster then restarts all sessions).
3. Apply the patch: `git apply AUDIT-F2_REGRESSION_TEST.patch`. Rebuild, run
   step 2 again (the third query returns `(null)` at once), and run
   `make check` (all tests pass, including the four new `window` queries).
