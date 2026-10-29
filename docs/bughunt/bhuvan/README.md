# Bhuvan — PostgreSQL bug-hunt work

Consolidated record of the bugs found, the fuzzing that found them, how to
reproduce each, and their upstream status. Part of CS-5187 project A3
("LLM-guided grammar-aware fuzzing of PostgreSQL"; team: Venu, Bhuvan, Gowtham).

## Fuzzing methods used

| Method | Entry point | What it does |
|---|---|---|
| Grammar fuzzer | `python -m pgfuzz run configs/*.yaml` | typed, scope-aware SQL; differential plan oracle + metamorphic oracles |
| Cross-version differential | `src/xversion/joinfuzz.py`, `joinfuzz2.py` | same query on master vs 18.6, results compared as multisets |
| Metamorphic fuzzer | `src/xversion/metafuzz.py` | TLP + NoREC oracles |
| Differential (hunter B/C) | `bugprogress/scripts/*.py` | code-reading + differential testing of recent features |
| Manual audit + probes | `bughunt/audit/`, `bughunt/audit2/` | 23 Oct 2026 correctness audit |

## Bugs (summary)

| Bug | Found by | Upstream | Status |
|---|---|---|---|
| BUG-01 JSON_TABLE collation | grammar fuzzer | **BUG #19768** | filed 16 Oct, awaiting committer reply |
| BUG-02 range containment NULL | metamorphic oracle `expr:scalar_sub` | **BUG #19793** | filed 23 Oct (Venu), patch sent |
| BUG #19766 shm_toc_insert assert | grammar fuzzer | **#19766** | reply sent (Bhuvan) |
| extended-stats non-finite MCV | manual test + code reading | pgsql-hackers | patch submitted (Bhuvan) |
| B-01 FULL JOIN NOT NULL folding | hunter B `fz2.py` | — | skipped (root cause in progress: hackers thread 7400) |
| C-01 duplicate-expression assert | hunter C fuzzers | pgsql-bugs | filed 27 Oct (Bhuvan), awaiting bug number |
| AUDIT-F1 NOT IN anti-join cast | audit + probes + fuzzers | pgsql-bugs | filed 23 Oct (Bhuvan) |
| AUDIT-F2 IGNORE NULLS hang | audit2 session | pgsql-bugs | filed 23 Oct (Bhuvan); Ishii replied 24 Oct |
| Candidate 2 crash-recovery | grammar fuzzer (seen once) | **#17731** | known upstream |

---

## Filed / acknowledged upstream

### 1. BUG-01 — JSON_TABLE never assigns collations (BUG #19768)
- **Found by:** grammar fuzzer. Assertion
  `Assert(list_length(rcexpr->inputcollids) == nopers)` in `execExpr.c:2078`,
  plus a silent wrong result and spurious "could not determine which collation"
  errors on the 18.6 release.
- **Filed:** 16 Oct 2026 by Venu Kummari as BUG #19768.
  - Report: https://www.postgresql.org/message-id/19768-3633daa830be95db@postgresql.org
  - Thread: https://www.postgresql.org/message-id/flat/19768-3633daa830be95db@postgresql.org
- **Status:** no committer reply yet.
- **Reproduce:** see `../BUG-01-json_table-collation.md`.
- **Evidence:** `evidence/bug01-*` (fuzzer query, TRAP backtrace, make-check log).

### 2. BUG #19766 — Assert in shm_toc_insert (Parallel Append + shared SubPlan)
- **Found by:** grammar fuzzer on an assert-enabled master build.
- **Bhuvan's addition:** the shared SubPlan does not need a partitioned table;
  an inheritance parent + child gives the same Parallel Append and crash.
- **Reproduce:**
  ```sql
  CREATE TABLE ip (a int);
  CREATE TABLE ic () INHERITS (ip);
  CREATE TABLE s (b int);
  EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF, BUFFERS OFF)
    SELECT * FROM ip WHERE a NOT IN (SELECT 1 FROM s, s s2);
  -- TRAP: failed Assert("toc->toc_entry[i].key != key"), shm_toc.c:190
  ```
- **Draft reply (from c.bhuvan@iitg.ac.in):** `replies/reply-19766-draft.txt`.

### 3. Extended-stats — `pg_restore_extended_stats()` accepts non-finite MCV frequencies
- **Found by:** manual testing + code reading (18 Oct 2026). Storing NaN/Inf
  in MCV frequencies makes the planner estimate ~1e100 rows (no crash).
- **Bhuvan's patch:** `patches/0001-Reject-non-finite-MCV-frequencies-in-pg_restore_exte.patch`.
- **Submitted:** pgsql-hackers. **Not a CVE** — hardening only (follows 7cb9060d
  and Ewan Young's attribute-stats thread).
- **Notes:** `replies/SUBMIT-extended-stats-nonfinite.txt`,
  `replies/extended-stats-nonfinite-NOTE.txt`.

---

## Found + root-caused (BUG-02 → #19793; B-01/C-01 still unfiled)

### 4. BUG-02 — range containment with a NULL element returns true/false instead of NULL
- **Found by:** the new metamorphic oracle (`expr:scalar_sub` rewrite), 23 Oct 2026,
  in the first 150 test cases it ran.
- **What it is:** `range @> elem` / `elem <@ range` planner support functions
  replace the call by a constant for empty/unbounded constant ranges, ignoring
  strictness, so NULL inputs yield `t`/`f` instead of NULL (a silent wrong result
  since PostgreSQL 17).
- **Reproduce:**
  ```sql
  SELECT c, '(,)'::int4range @> c AS a, 'empty'::int4range @> c AS b,
         NOT ('empty'::int4range @> c) AS d
  FROM (VALUES (NULL::int), (1)) v(c);
  -- NULL row shows  t | f | t  (expected all NULL)
  ```
- **Status:** **filed 23 Oct 2026 by Venu Kummari as BUG #19793**; patch sent as a reply.
  - Thread: https://www.postgresql.org/message-id/19793-16d3a1bf33dff0fb@postgresql.org
- **Report:** `../BUG-02-range-containment-null.md`.
- **Patches:** `patches/v1-0001-range-containment-null-master.patch`,
  `patches/v1-0001-range-containment-null-REL_17_18.patch`.
- **Evidence:** `evidence/bug02-*`.

### 5. B-01 — FULL JOIN NOT NULL folding (PG19 regression)
- **Found by:** hunter B differential fuzzer (`fz2.py`), master vs 18.6.
- **Status:** skipped — same root cause is an open pgsql-hackers item (commitfest 7400, in progress).
- **Report:** `../new/B-01-full-join-notnull-folding.md`, `../../bugprogress/B-01-*`.

### 6. C-01 — dependencies duplicate-expression assertion
- **Found by:** hunter C differential fuzzers.
- **Status:** **filed 27 Oct 2026 by Bhuvan** (assertion-only; distinct from #19789/#19772).
- **Report:** `../new/C-01-dependencies-duplicate-expression-assert.md`,
  `../../bugprogress/C-01-*`.

---

## Audit findings (23 Oct 2026)

### 7. AUDIT-F1 — NOT IN → anti-join conversion ignores an implicit cast on the sub-select side
- **Found by:** manual audit + probes + fuzzers (jtfuzz/ixfuzz/ptfuzz/hashcheck/jsoneq/intervalrt).
- **What it is:** a wrong-result regression from commit `383eb21ebf`; present in 19rc1
  and master, absent in 18.6.
- **Status:** **filed 23 Oct 2026 by Bhuvan** on pgsql-bugs; patch + test.
  - Thread: https://www.postgresql.org/message-id/PN0P287MB090375874C6D5433282EC9DFA7642@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM
- **Report:** `audits/POSTGRESQL_BUG_AUDIT.md`, `audits/AUDIT-F1_FINAL_REPORT.txt`.
- **Reproduce:** `psql -X -f audits/AUDIT-F1-reproducer.sql`.

### 8. AUDIT-F2 — IGNORE NULLS frame-scan hang
- **Found by:** audit2 session.
- **Status:** **filed 23 Oct 2026 by Bhuvan** on pgsql-bugs; committer Ishii replied 24 Oct.
  - Thread: https://www.postgresql.org/message-id/PN0P287MB09038F3BD9921EBACF5646F6A7632@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM

---

## Seen once, known upstream

### 9. Candidate 2 — crash recovery "could not create file base/5/165792: File exists"
- **Found by:** grammar fuzzer (seen once).
- **Status:** known as BUG #17731; not reproduced by us.
- **Evidence:** `evidence/cand2-*`.

---

## Upstream status at a glance

| Bug | Upstream ID | Status |
|---|---|---|
| BUG-01 | #19768 | filed, awaiting committer reply |
| BUG-02 | #19793 | filed 23 Oct (Venu), patch sent |
| BUG #19766 | #19766 | reply sent |
| extended-stats | (hackers thread) | patch submitted |
| B-01 | — | skipped (hackers thread 7400) |
| C-01 | pgsql-bugs | filed 27 Oct (Bhuvan) |
| AUDIT-F1 | pgsql-bugs | filed 23 Oct (Bhuvan) |
| AUDIT-F2 | pgsql-bugs | filed 23 Oct (Bhuvan); Ishii replied |
| Candidate 2 | #17731 | known |

Every claim above comes from a real run; the evidence files back the
reproducers and results.

## Additional context
- `HANDOFF-2026-10-18.md` — the updated bug-hunt handoff (18 Oct 2026).
- `fuzzers/` — the actual fuzz/differential scripts used (grammar-hunt era + the
  23 Oct audit fuzzers: jtfuzz/ixfuzz/ptfuzz/hashcheck/jsoneq/intervalrt, and
  audit2 fuzzers nnfuzz/winfuzz/rtcheck).
