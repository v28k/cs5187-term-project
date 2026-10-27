# AUDIT-F2 — Final verification verdict

**Primary verdict: CONFIRMED LOCAL BUG.**

This verdict means the unpatched upstream code reproducibly fails to terminate
for valid SQL whose result is well-defined, the root cause is established from
source and a debugger, and the proposed patch fixes it with adequate
regression evidence and no observed regressions. It does **not** mean the
report has been accepted upstream, and nothing has been sent.

The verification was done independently of the earlier AUDIT-F2 conclusion:
fresh builds, a fresh reproduction, an external watchdog instead of in-server
cancellation, an independently justified oracle, and a re-derived root cause.
Two errors in the earlier work were found and corrected (below). The core
finding stands.

## 1. Executive summary

* **Does the query hang on clean unpatched upstream?** Yes. On the current
  `origin/master` (`126976a8ff`) and current `origin/REL_19_STABLE`
  (`015f4c9fc3`), the minimal query runs forever. A debugger shows the loop
  counter advancing at ~1.8×10⁸/s on a **one-row** table; the backend is in
  state `R`, burning one core. This is nontermination, not slow execution.
* **Independently established expected result:** a single row containing NULL.
  With no `ORDER BY` all rows are peers (`ref/select.sgml:1016`), `EXCLUDE
  GROUP` removes the current row and its peers (`syntax.sgml:1983`), so the
  frame is empty; `first_value` over an empty frame is NULL, and `nth_value`
  "returns NULL if there is no such row" (`func-window.sgml:226`).
* **Root cause confirmed:** `ignorenulls_getfuncarginframe()` calls
  `row_is_in_frame()` for positions past the end of the partition, violating
  that function's documented precondition. For a frame ending at UNBOUNDED
  FOLLOWING (or a ROWS offset past the partition) with EXCLUDE GROUP / TIES
  and no `ORDER BY`, `row_is_in_frame()` returns 0 ("excluded") for every such
  position, so the loop never reaches the partition-end check that only
  `window_gettupleslot()` performs, and never hits `CHECK_FOR_INTERRUPTS()`.
* **Does the patch fix it without regressions?** Yes, in all tests run. The
  6 hanging cases terminate and return the oracle-justified values; core
  regression is 239/239 on patched master and patched REL_19_STABLE;
  isolation is 134/134 on patched master; a 24,000-query fuzz against an
  independent oracle has 0 mismatches. No regression appeared against the
  239/239 unpatched baseline. Relevant TAP suites pass on a TAP-enabled
  patched build: psql 253/253 (including `020_cancel` for SIGINT cancellation
  and a 23-assertion AUDIT-F2 test), test_misc 168/168, pg_ctl 54/54.
* **Duplicate?** No. The nearest item, "nodeWindowAgg.c IGNORE NULLS abs
  overflow" (pgsql-hackers, 2026-10-21, unapplied), is a different defect in
  the same function. No report of this hang exists in the searched scope.
* **Ready to send upstream?** The evidence supports submission. Per the
  audit's standing rule, it is held as an unsent draft pending the user's
  review and explicit approval.

## 2. Evidence for the bug

| # | Evidence | Source |
|---|---|---|
| E1 | 6 of 17 matrix cases do not finish within a 6 s external watchdog on unpatched master; the controller kills the process group (not reliant on in-server cancellation). The 6 are exactly the EXCLUDE GROUP / TIES + frame-end-past-partition + no-ORDER-BY cases. | `v/evidence/matrix_unpatched.json`, `v/matrix.py` |
| E2 | Nontermination, not slowness: the loop counter `pos` advances 341,115,073 → 522,435,201 → 701,118,995 over 2 s; state `R`; CPU ticks 212→324→432. On a one-row table, any valid position is 0. | `v/evidence/backtrace.txt`, `v/bt5.sh` |
| E3 | Affected on the current tips of both live branches: master `126976a8ff` and REL_19_STABLE `015f4c9fc3`. No commit touches `nodeWindowAgg.c`/`windowfuncs.c` between the tested revisions and the current tips. | `v/upstream.sh` |
| E4 | Not affected on 18.6: the `IGNORE NULLS` syntax does not parse (feature is new in 19). | `logs/hang_r18_t1_min.out` |
| E5 | Patched build: the same 6 cases finish and return oracle-justified values; all 17 cases agree with controls. | `v/evidence/matrix_patched.json` |

## 3. Evidence against / limits of the claim (examined and resolved)

| # | Point | Resolution |
|---|---|---|
| A1 | A 6 s timeout alone could be "slow", not infinite. | Refuted by E2: counter advances monotonically at ~1.8×10⁸/s; reaching INT64_MAX would take ~1.6 years. |
| A2 | The expected value might itself be nonobvious (e.g. IGNORE NULLS over an empty frame). | Resolved from docs: empty frame → NULL for both functions. Confirmed by the RESPECT NULLS control (`c1`) and the aggregate-path control (`c2`), both returning NULL immediately on unpatched. |
| A3 | The earlier report's oracle (`array_agg FILTER`) might not match the frame/exclusion/peer semantics. | For the empty-frame cases the aggregate path returns NULL (verified, `c2`). For nonempty frames the matrix uses hand oracles (`c4`, `c5`, `c8`, `c14`), independently derived, and both builds match them. |
| A4 | Could be a duplicate of the known `abs()` overflow report. | Refuted: that bug needs a huge negative `relpos` to overflow `int abs(relpos)`; our cases use `relpos = 0` (first_value) or small positive (nth_value), and the loop counter here is `int64 abs_pos`. Different trigger, different variable, different fix hunk. |

**Two earlier-work errors found and corrected during this verification:**
* The initial matrix hand-oracle for one case joined output rows with `,`
  instead of the newline `psql -A` emits (a test-encoding bug, not a server
  bug). Corrected; both builds then matched.
* Another hand-oracle ignored a `WHERE x IS NULL` that filters before
  windowing. Corrected to test the intended nonempty frame; both builds match.
Neither affected the hang finding; both are documented in the matrix.

## 4. SQL semantics and expected outputs

Minimal trigger:

```sql
SELECT first_value(x) IGNORE NULLS OVER (
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP
) FROM (VALUES (1)) v(x);
```

* Peers: "all rows are peers if there is no `ORDER BY`" — `ref/select.sgml:1016`.
* `EXCLUDE GROUP` "excludes the current row and its ordering peers from the
  frame" — `syntax.sgml:1983`.
* Therefore the frame is empty. `first_value` returns the value at the first
  row of the frame (`func-window.sgml:196`); with no such row the result is
  NULL. `nth_value` "returns NULL if there is no such row"
  (`func-window.sgml:226`).
* `IGNORE NULLS` cannot change an empty-frame result: there is no row, null or
  not, to return. Default is `RESPECT NULLS` (`func-window.sgml:274`).

Expected per case: see `AUDIT-F2_VERIFICATION_MATRIX.md`.

## 5. Root cause (source-level)

All line numbers at `126976a8ff`, `src/backend/executor/nodeWindowAgg.c`,
unless noted.

1. `window_first_value` / `window_nth_value` (`windowfuncs.c:663,719`) call
   `WinGetFuncArgInFrame(..., WINDOW_SEEK_HEAD, ...)`; with `IGNORE NULLS`
   (`WinGetFuncArgInFrame`, line 4041) control enters
   `ignorenulls_getfuncarginframe()` (line 3408).
2. That function walks forward from `frameheadpos`, calling
   `row_is_in_frame(winobj, abs_pos, slot, true)` (line 3478) each iteration
   and skipping to `advance` on a 0 result (line 3482) **without fetching the
   row**.
3. `row_is_in_frame()`'s header (line 1491) states: "The caller must have
   already determined that the row is in the partition." Its only frame-end
   tests are for `END_CURRENT_ROW` and `END_OFFSET` (lines 1524–1578); a frame
   ending at UNBOUNDED FOLLOWING has none. Its exclusion branch returns 0
   unconditionally when `node->ordNumCols == 0` for EXCLUDE GROUP, and for
   EXCLUDE TIES when `pos != currentpos` (lines 1586–1601).
4. So once `abs_pos` passes the last row, every call returns 0. The loop never
   calls `window_gettupleslot()` — the only place that detects
   `pos >= spooled_rows` (line 3299) — and `abs_pos` (an `int64`, line 3416)
   grows until it would overflow (~9.2×10¹⁸). No `CHECK_FOR_INTERRUPTS()` runs
   on this path.
5. Debugger confirmation (E2): frame 1 is `row_is_in_frame`, frame 2 is
   `ignorenulls_getfuncarginframe`, `relpos=0`, `abs_pos` type `int64`, counter
   advancing.
6. Why neighbours terminate (all verified in the matrix): with `ORDER BY`
   (`c3`, `c4`) positions past the partition are not peers so
   `row_is_in_frame()` returns 1 and `window_gettupleslot()` ends the loop;
   with a small finite end offset (`c13`) it returns -1; `last_value` (`c11`)
   scans backward and stops at `abs_pos < 0`; RESPECT NULLS (`c1`) fetches the
   row first, honouring the contract.

**Is this the right layer?** Yes. `row_is_in_frame()`'s contract already puts
partition-membership on the caller, and the RESPECT NULLS caller already obeys
it. Fixing `ignorenulls_getfuncarginframe()` to establish membership (as
`window_gettupleslot()` does) is consistent with that contract and minimal. A
lower-level alternative — making `row_is_in_frame()` itself return -1 past the
partition end — would change a documented precondition and touch every caller;
it is noted as an option for the committer but not adopted here.

## 6. Reproduction and patch results

* Builds (assertions on, `--enable-cassert --enable-debug`, gcc 13.3.0,
  `-fwrapv` in CFLAGS): unpatched master `126976a8ff`, patched master, patched
  REL_19_STABLE `fc189eb750` (an ancestor of the current REL_19 tip; no
  intervening `nodeWindowAgg.c` change). All binaries confirmed by
  `SELECT version()` and `pg_config --configure`.
* Reproduction: `v/matrix.py` under a 6 s external watchdog on a disposable
  cluster; recovery by SIGKILL of the wedged backend; cluster recovered each
  time.
* Patch: `AUDIT-F2_REGRESSION_TEST.patch` (sha256 of the diff `4c76cd5bd3`,
  identical in the `fix` and `r19fix` worktrees). Applies cleanly to current
  `origin/master` and `origin/REL_19_STABLE`.
* Test suites: core regression 239/239 (patched master, patched REL_19);
  isolation 134/134 (patched master); unpatched baseline 239/239. The new
  `window.sql` queries never finish on the unpatched server (pg_regress killed
  by a 180 s watchdog). Details and exact log paths in
  `AUDIT-F2_TEST_RESULTS.md`.

## 7. Operational impact (each claim tested separately)

Tested on a disposable unpatched cluster; see `v/evidence/operational.txt`.

| Claim | Result | Evidence |
|---|---|---|
| `statement_timeout` does not stop it | Confirmed: backend still `active` 5 s after a 2 s timeout | `v/barrier.sh` |
| `pg_cancel_backend()` does not stop it | Confirmed: still `active` 3 s after cancel | `v/barrier.sh` |
| `pg_terminate_backend()` does not stop it | Confirmed: still `active` 3 s after terminate | `v/barrier.sh` |
| `pg_ctl stop -m fast` does not complete | Confirmed: "server does not shut down", exit 1 | earlier `shutdown_demo.sh`, `logs/server-mh.log` |
| An unrelated `ALTER DATABASE … SET TABLESPACE` stalls | Confirmed cleanly: 0.23 s normally, blocks past 12 s with the hang present, waiting on `IPC / ProcSignalBarrier` | `v/barrier2.sh` |
| Recovery | SIGKILL of the backend → postmaster restarts all sessions (crash recovery); cluster recovered every time | all scripts |

Distinctions, stated precisely: this is (a) a query that does not terminate,
(b) a backend that does not respond to interrupts or absorb a
ProcSignalBarrier, and therefore (c) an unrelated barrier-emitting command on
another database stalls while the backend runs, and (d) fast shutdown cannot
complete. Any role that can run a SELECT can trigger it, with no table and no
special privilege. It was not tested whether ordinary queries on unrelated
databases (that emit no barrier and take no conflicting lock) are affected;
those are expected to run normally, so this is a targeted availability problem,
not a demonstrated full outage.

## 8. Duplicate-search scope

* postgresql.org site search (all lists): symptom phrases, function names,
  source symbols — `first_value/nth_value IGNORE NULLS`, `EXCLUDE GROUP/TIES`,
  `ignorenulls_getfuncarginframe`, `row_is_in_frame`, `infinite loop`, `hang`,
  `does not terminate`, `cannot cancel`. 0 relevant hits
  (`v/evidence/dupfinal.txt`).
* Per-day list scan (earlier): pgsql-bugs 2026-05-01→10-24, pgsql-hackers
  2026-06→10-24. Window-related reports found (#19532/#19533 run-condition,
  #19713 qual pushdown, #19731/#19732 EXCLUDE TIES in the RESPECT NULLS path)
  — none is this hang.
* git history: no commit changes the loop's end condition; current master and
  REL_19 tips unchanged in this file since the tested revisions.
* The nearest open thread, "nodeWindowAgg.c IGNORE NULLS abs overflow"
  (2026-10-21), is a different defect (see A4) and is still unapplied upstream.

Not independently verifiable: private security reports; messages the archive
does not index; the site search ignores its date filter.

## 9. Outstanding limitations

* **TAP tests: run (follow-up).** `IPC::Run` was installed into `~/perl5`
  (no root) and the patch rebuilt with `--enable-tap-tests`. The relevant
  suites pass on the patched build: psql 253/253 (incl. `020_cancel` and a
  23-assertion AUDIT-F2 test, `scripts/verify/099_audit_f2.pl`), test_misc
  168/168, pg_ctl 54/54 (`AUDIT-F2_TEST_RESULTS.md` §TAP). There is no
  upstream TAP dedicated to window functions; TAP was run only on the patched
  build (the unpatched reproducer would hang the harness).
* **No ICU, no concurrency.** Built `--without-icu`; no isolation test was
  written specifically for this bug (the hang is single-backend and does not
  need one).
* **Full-outage scope not established.** Only barrier-emitting / fast-shutdown
  impacts were demonstrated (section 7); a broader denial-of-service was not
  claimed or tested.
* **Platform.** Verified only on x86_64 Linux (WSL2). The defect is
  control-flow logic with no platform dependency, but it was not run elsewhere.

## 10. Recommendation

The finding is a genuine, reproducible upstream termination bug, correctly
described, with a minimal fix that passes the available tests and no observed
regressions, including the relevant TAP suites. The upstream draft
(`AUDIT-F2_UPSTREAM_REPORT.md`) is suitable to send to `pgsql-bugs`, subject
to the user's review and explicit approval. Nothing has been sent.
