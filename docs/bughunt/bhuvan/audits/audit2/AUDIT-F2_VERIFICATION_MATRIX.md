# AUDIT-F2 verification matrix

Each case was run in its own `psql` subprocess under a 6 s **external**
wall-clock watchdog (`scripts/verify/matrix.py`): the controller kills the
process group on timeout and does not depend on `statement_timeout`,
`pg_cancel_backend()`, `pg_terminate_backend()` or graceful shutdown. A case
that is killed is recorded as `timeout` (candidate nontermination — see the
backtrace evidence in `AUDIT-F2_FINAL_VERDICT.md` §2 E2), never silently as a
confirmed infinite loop from the timeout alone.

* Unpatched server: master `126976a8ff` (binary `install/m`, port 5482).
* Patched server: master `126976a8ff` + `AUDIT-F2_REGRESSION_TEST.patch`
  (binary `install/fix`, port 5485).
* Expected values are independently justified (docs or hand derivation), not
  taken from the patched build. `psql -A -t` prints result rows separated by
  newlines; `\n` below is that separator.
* Raw results: `scripts/verify/evidence/matrix_unpatched.json`,
  `matrix_patched.json`.

| ID | Window spec (first_value/nth_value unless noted) | Input | Expected | Unpatched | Patched | Factor isolated |
|---|---|---|---|---|---|---|
| t1 | `ROWS UNBOUNDED PRECEDING..UNBOUNDED FOLLOWING EXCLUDE GROUP`, no ORDER BY | `(1)` | `NULL` | **timeout** | `NULL` ✓ | the bug: empty frame, forward scan |
| c1 | same, **RESPECT NULLS** (default) | `(1)` | `NULL` | `NULL` ✓ | `NULL` ✓ | null-treatment is the trigger |
| c2 | same, **aggregate oracle** `(array_agg FILTER …)[1]` | `(1)` | `NULL` | `NULL` ✓ | `NULL` ✓ | independent oracle = NULL |
| c3 | `ORDER BY 1 ROWS …UNBOUNDED FOLLOWING EXCLUDE GROUP` (all peers, ordNumCols>0) | `(1)` | `NULL` | `NULL` ✓ | `NULL` ✓ | ORDER BY present ⇒ terminates |
| c4 | `ORDER BY x ROWS …UNBOUNDED FOLLOWING EXCLUDE GROUP` (distinct groups) | `(1),(2)` | `1:2\n2:1` | `1:2\n2:1` ✓ | `1:2\n2:1` ✓ | nonempty frame returns right value |
| c5 | `ROWS …UNBOUNDED FOLLOWING` (no exclusion) | `(1)` | `1` | `1` ✓ | `1` ✓ | exclusion is the trigger |
| c6 | `ROWS …UNBOUNDED FOLLOWING EXCLUDE CURRENT ROW` | `(1)` | `NULL` | `NULL` ✓ | `NULL` ✓ | EXCLUDE CURRENT ROW is bounded |
| t7 | `ROWS …UNBOUNDED FOLLOWING EXCLUDE TIES`, current row NULL | `(NULL)` | `NULL` | **timeout** | `NULL` ✓ | EXCLUDE TIES also triggers |
| c8 | same, current row non-NULL | `(5)` | `5` | `5` ✓ | `5` ✓ | value found at current row ⇒ terminates |
| t9 | `nth_value(x,2) ROWS …UNBOUNDED FOLLOWING EXCLUDE GROUP` | `(1)` (x=1) | `NULL` | **timeout** | `NULL` ✓ | nth_value on same path |
| t10 | `nth_value(x,2) ROWS CURRENT ROW..UNBOUNDED FOLLOWING EXCLUDE TIES` | `(1)` (x=1) | `NULL` | **timeout** | `NULL` ✓ | 2nd non-null absent ⇒ scan past end |
| c11 | `last_value(x) ROWS …UNBOUNDED FOLLOWING EXCLUDE GROUP` | `(1)` | `NULL` | `NULL` ✓ | `NULL` ✓ | backward scan stops at <0 |
| t12 | `ROWS …AND 1000000000000 FOLLOWING EXCLUDE GROUP`, no ORDER BY | `(1)` | `NULL` | **timeout** | `NULL` ✓ | finite offset past partition ⇒ same path |
| c13 | `ROWS …AND 3 FOLLOWING EXCLUDE GROUP`, no ORDER BY | `(1)` | `NULL` | `NULL` ✓ | `NULL` ✓ | small offset ⇒ row_is_in_frame returns -1 |
| c14 | `ROWS …UNBOUNDED FOLLOWING` (no exclusion), full frame | `(NULL),(7)` | `7\n7` | `7\n7` ✓ | `7\n7` ✓ | IGNORE NULLS skips NULL, keeps 7 |
| t15 | `RANGE …UNBOUNDED FOLLOWING EXCLUDE GROUP`, no ORDER BY | `(1)` | `NULL` | **timeout** | `NULL` ✓ | RANGE mode also triggers |
| c16 | t1 frame, empty input | `WHERE false` | 0 rows | 0 rows ✓ | 0 rows ✓ | nothing to scan |

Totals — unpatched: 11 finished (all correct), 6 timeout, 0 oracle mismatch.
Patched: 17 finished (all correct), 0 timeout, 0 oracle mismatch.

## Causal reading

* **Null treatment** (t1 vs c1/c2): the hang needs `IGNORE NULLS`; RESPECT
  NULLS and the aggregate path return immediately.
* **Exclusion** (t1 vs c5): without an exclusion clause the frame is nonempty
  and the function returns at once. EXCLUDE GROUP and EXCLUDE TIES both trigger
  (t1, t7, t9, t10, t15); EXCLUDE CURRENT ROW does not (c6).
* **Ordering** (t1 vs c3/c4): any `ORDER BY` makes the loop terminate, because
  positions past the partition are no longer peers.
* **Frame end** (t1/t12 vs c13): UNBOUNDED FOLLOWING or a finite offset past
  the partition triggers; a small finite offset does not (row_is_in_frame
  returns -1).
* **Direction** (t1 vs c11): only forward-scanning functions (first_value,
  nth_value) hang; last_value scans backward and stops at position < 0.
* **Function** (t1, t9): both first_value and nth_value with valid positive n.
* **Mode** (t1 vs t15): ROWS and RANGE both trigger.

Each timeout case differs from a terminating control by exactly one factor,
isolating the cause to: forward IGNORE NULLS scan + peer-excluding exclusion +
no ORDER BY + frame end at/after the partition end.

## Debugger evidence (nontermination, not slowness)

`scripts/verify/evidence/backtrace.txt` (fresh unpatched build, t1 query):

```
PID=63823 procstate=R
sample1: pos@entry=341115073  cpu_ticks=212  procstate=R
sample2: pos@entry=522435201  cpu_ticks=324  procstate=R
sample3: pos@entry=701118995  cpu_ticks=432  procstate=R
```

`pos` is `row_is_in_frame`'s argument = the loop's `abs_pos` (`int64`,
confirmed via `whatis`). It advances ~1.8×10⁸ per second on a one-row table,
where any valid position is 0. Frame 2 is `ignorenulls_getfuncarginframe` with
`relpos=0`.
