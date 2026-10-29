# Bug-hunt log (cloud session)

Goal: find a previously unknown PostgreSQL bug (crash, assertion, or wrong
result), file it upstream, and get it accepted.

## Setup (16 Oct 2026)

| Item | Value |
|---|---|
| Test server | PostgreSQL `20devel` (master) at `26bd08fb`, `--enable-cassert --enable-debug`, `-O1`, ports 5432/5433 (campaign), 5434 (manual) |
| Reference server | PostgreSQL 18.6 (`REL_18_STABLE` at `92d47d5`), port 5435 |
| Machine | 4 cores, 15 GB RAM, Linux container |
| Executor selftest | 10/10 on this build |
| Unit tests | 84 passed, plus 7 new in `tests/test_differential.py` |

Runs:

* `scripts/cloud_hunt.sh` - grammar campaign (`configs/cloud_hunt.yaml`, 2 trials x 6 h).
* `scripts/joinfuzz_loop.sh` - cross-version join fuzzer (`src/xversion/joinfuzz.py`):
  same query on master and on 18.6, results compared as multisets.
* `src/xversion/joinfuzz2.py` - v2: bigger mixed-type tables, random planner
  GUCs on master (eager aggregation forced, join methods off, partitionwise,
  forced parallel), GROUP BY over joins, self-joins, UNION ALL, grouping sets.

## Where we looked, and why

Master commits since `20devel` was stamped (29 Jun 2026) that touch the
planner, with many follow-up fixes (a bug cluster is a good place for a
sibling bug):

* outer join -> anti join reduction (a812cf64, 2ce5a57b, 02119d6c, f863be3e,
  31c002aa, ad4b80b6): read `reduce_outer_joins_pass2`,
  `forced_null_var_is_nonnullable`, `find_safe_quals`,
  `strip_redundant_nullability_quals`. Checked: system columns excluded from
  whole-row proofs, NOT VALID not-null constraints excluded
  (`ATTNULLABLE_VALID`), virtual generated columns expanded before the pass,
  inheritance parents skipped. No hole found by reading.
* eager aggregation (fixes d764d61a, ffeda042, 3a08a2a8, bd94845e): read
  `setup_eager_aggregation`, `init_grouping_targets`,
  `get_expression_sortgroupref`. Equal-image check present for grouping and
  join keys.
* join removal on the jointree (2ebf25e7 + ~6 fixes), self-join elimination.

## Candidates

| # | Source | Verdict |
|---|---|---|
| 1 | grammar hunt, `wrong_result` under `enable_hashagg=off` | **False positive** in our oracle: `ARRAY(SELECT ... EXCEPT ALL ...)` has no ORDER BY, so element order depends on the plan. Fixed `eval/differential.py` `eligible()`, test added. |
| 2 | grammar hunt trial 0, `assertion` (`list_length(rcexpr->inputcollids) == nopers`, execExpr.c:2078) | **REAL BUG**, see [BUG-01](BUG-01-json_table-collation.md): JSON_TABLE never assigns collations to its context item / PASSING args. Wrong result and spurious collation errors on 18.6 too. Patch + tests ready. Reported as **BUG #19768**; v1 patch verified (239/239 `make check`, pgindent clean). |
| 4 | metamorphic oracle (`expr:scalar_sub`), sample of 150 test cases, 23 Oct | **REAL BUG**, see [BUG-02](BUG-02-range-containment-null.md): range containment with a constant empty/unbounded range returns false/true for a NULL element (17, 18, master). Patch + tests ready. |
| 3 | grammar hunt trial 1, `wrong_result` under `no_hashagg` / `parallel` | False positives, `ARRAY(SELECT ...)` again (run started before the filter fix reached it). |

## Tooling issues found on the way

* The failure directory for signature `cde9712bc8db` saved test case 18784
  (a DELETE that does not crash) as `testcase.sql`; the crashing statement was
  test case 13306 (found via `events.jsonl` and the TRAP backtrace, which shows
  `ExecInitTableFuncScan`). The failure writer should store the test case
  that produced the signature first, or all of them.
* `pkill -f PATTERN` from a shell whose own command line contains PATTERN
  kills that shell; use `pkill -f "[p]attern"` in a separate command.
