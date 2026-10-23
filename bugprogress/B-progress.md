# Hunter B progress report (23 Oct 2026)

Method: audit PG19 / 20devel optimizer and executor features added since mid-2025, then
check them differentially (master vs 18.6, and master under different planner settings).

## 1. Environment

| Item | Value |
|---|---|
| master (cassert, -O1) | 20devel 126976a8 (23 Oct 2026), port 5433 |
| reference | 18.6 (REL_18_STABLE release build, no ICU), port 5435 |
| patched master (B-01 patch) | tmp_install server, port 5440 |
| REL_19_STABLE | fc189eb7 (19rc1), source only (not built) |
| REL_17_STABLE | build started, stopped on request (not available) |

Setup problems hit and fixed: `apt-get` had failed silently (ICU and flex missing), so
`apt-get update` + reinstall was needed. `/root` needed `o+rx` so user `pg` can run the
binaries. The master tree has no `--enable-depend`, so after changing a header you **must**
`make clean` (otherwise the server segfaults in `make check`).

## 2. Results summary

| ID | Kind | Status | Fileable? | Confidence |
|---|---|---|---|---|
| **B-01** | PG19 regression: FULL JOIN error after NOT NULL-based IS NULL folding | confirmed 3/3, root cause, patch, make check 239/239 | **yes** (read the related hackers thread first) | medium-high |
| B-dup-1 | wrong result, chain of LEFT JOINs with constant | confirmed on master and 18.6 | **no**, duplicate of BUG #19765 | high (that it is a dup) |
| B-u-1 ... B-u-8 | untested / partly tested ideas | see section 5 | not yet | low |

Full filing report for B-01: `B-01-full-join-notnull-folding.md` (+ `.sql`, `.patch`) in this
folder (copy of `docs/bughunt/new/B-01-*`).

## 3. Valid bug: B-01 (short version)

```sql
CREATE TABLE fa (x int NOT NULL);
CREATE TABLE fb (y int);
INSERT INTO fa VALUES (0), (1);
INSERT INTO fb VALUES (0), (NULL);
SELECT * FROM fa FULL JOIN fb ON (fa.x IS NULL) = (fb.y IS NULL);
-- 18.6: 3 rows (Hash Full Join).   19rc1 / master:
-- ERROR: FULL JOIN is only supported with merge-joinable or hash-joinable join conditions
```

- Cause: `eval_const_expressions()` folds `fa.x IS NULL` → `false` using the NOT NULL
  constraint (PG19 commit e2debb64380 and follow-ups). The ON clause becomes
  `fb.y IS NOT NULL`, which mentions only one side, so the FULL JOIN has no hashable clause.
- Also triggered by `IS NOT NULL` on a primary key, `bool IS UNKNOWN`, `ROW(...) IS NULL`.
- Patch: do not use NOT NULL proofs while preprocessing FULL JOIN quals
  (`PlannerInfo.inFullJoinQuals`), plus a regression test in `join.sql`.
- Before filing: read pgsql-hackers "[PG19] Wrong results from NOT NULL-based expression
  simplification" (around 17 Oct 2026). If it reworks the same code, reply there instead.

## 4. Duplicate: B-dup-1 (do NOT file)

```sql
CREATE TABLE ta (a int); CREATE TABLE tb (b int); CREATE TABLE tc (c int); CREATE TABLE td (d int);
INSERT INTO ta VALUES (3); INSERT INTO tb VALUES (1); INSERT INTO tc VALUES (3); INSERT INTO td VALUES (1);
SELECT * FROM td LEFT JOIN ta ON ta.a = 3 LEFT JOIN tb ON ta.a = tb.b LEFT JOIN tc ON tc.c = tb.b;
-- master and 18.6 return 1 | 3 | NULL | 3 ; correct is 1 | 3 | NULL | NULL
```

Same root cause as **BUG #19765** (16 Oct 2026, "wrong result from a chain of left joins since
v16"): `reconsider_outer_join_clauses()` replaces a cloned outer-join clause with TRUE after
constant propagation. Patches under discussion (Tender Wang, Nitin Motiani, Richard Guo), not
committed in master 126976a8. Our variant takes the constant from a degenerate ON clause instead
of WHERE. It is useful as an extra test case in that thread. Variants:
`scripts/B-dup19765-variants.sql`.

## 5. Untested or partly tested candidates (ideas, NOT confirmed bugs)

| ID | Area | Idea / suspected weak assumption | What was done | Next step |
|---|---|---|---|---|
| B-u-1 | NOT IN → anti join (383eb21e) | `sublink_testexpr_is_not_nullable()` checks the sub-select output column, not the coercion applied to the Param. A user-defined **implicit cast** whose function returns NULL for a non-null input would make NOT IN (NULL → row dropped) differ from the anti join (row kept). | Code read only | Create `CREATE CAST ... AS IMPLICIT` with a non-strict function that returns NULL; compare `x NOT IN (SELECT y ...)` with `enable_*` variants and 18.6 |
| B-u-2 | B-01 siblings | Other places where the PG19 NOT NULL folding (COALESCE, IS DISTINCT FROM, BooleanTest) might turn a working query into a planning error (e.g. FULL JOIN with `IS DISTINCT FROM NULL`, merge-join-only FULL JOIN with sort keys). | Five variants tested, all covered by the B-01 patch | Fuzz FULL JOIN ON clauses with all foldable forms |
| B-u-3 | RI fast path (ri_FastPathCheck, many 2026 fixes) | Concurrency: lock/snapshot ordering, `TM_SelfModified` returning "not found" (SPI keeps scanning), wCTE that updates the PK and inserts the FK in one statement. | Code read; no functional gap found single-session | Isolation tests (two sessions, REPEATABLE READ / READ COMMITTED), wCTE cases, compare with 18.6 (SPI path) |
| B-u-4 | Eager aggregation | Reading found it well fenced (plain Vars, BTEQUALIMAGE with the real collation, same-type EC). | Collation test made; eager aggregation was not chosen by the planner, so it is not really tested | Force it with `min_eager_agg_group_size`, use the regression-test schema shape, compare `enable_eager_aggregate` on/off |
| B-u-5 | JSON_TABLE PLAN clause (86ab7f4c, new syntax) | PLAN (OUTER/INNER/UNION/CROSS) semantics vs an equivalent hand-written query; NULL / empty arrays. | Not started | Write the equivalent lateral `jsonb_path_query` joins and compare |
| B-u-6 | ON CONFLICT DO SELECT (88327092) and ON CONFLICT arbiter changes (dc5f8cb9, 62e46c00) | Arbiter inference with expression indexes simplified by const folding (related thread mentions ON CONFLICT failures). | Not started | Expression indexes + NOT NULL columns + virtual generated columns |
| B-u-7 | Grouping-expression references / GROUPING() in subqueries (415100aa) | Correlated subquery referencing grouped expressions, with grouping sets. | Not started | Compare with an equivalent LATERAL query |
| B-u-8 | Outer join → anti join reductions | 43,000 fuzz queries agreed with 18.6; whole-row tests on zero-column tables and inheritance `NOT NULL ... NO INHERIT` parents only reasoned about. | Partly tested | Add zero-column tables, inheritance children with NULLs, partitioned tables to `B-fz1.py` |

## 6. Features audited with no bug found

- Outer join → anti join (a812cf64, 2ce5a57b, 02119d6c, f863be3e, ad4b80b6): code read plus
  `B-fz1.py`, 43,000 queries, about 10% reduced to anti joins, 0 diffs vs 18.6, 0 TRAPs.
- NOT IN → anti join (383eb21e): nullingrels, inheritance, NOT VALID, grouping sets,
  set operations all handled (except B-u-1).
- `ROW(...) IS [NOT] NULL` folding (cb7b7ec7): per-field scalar tests, matches executor.
- Eager aggregation (see B-u-4) and RI fast path (see B-u-3): by reading only.
- `B-fz2.py` (PlaceHolderVar-producing subqueries, LATERAL, UNION ALL, GROUP BY/DISTINCT
  subqueries, sort keys, master vs 18.6 plus random planner settings): 120,500 queries. It found
  B-01 and B-dup-1. Diffs where 18.6 errors and master works were treated as improvements.

## 7. Tools (in `scripts/`)

- `B_h.py`: psycopg helper (run a query under `SET` variants, compare sorted multisets).
- `B-fz1.py SEED N`: outer-join reduction fuzzer (needs master 5433 and 18.6 5435;
  recreates tables t1..t4 in database `postgres`).
- `B-fz2.py SEED N DB`: PHV/LATERAL/appendrel fuzzer, compares with 18.6 and with planner
  settings. Use a separate DB per process (e.g. `f1`, `f2`).
  Known noise: the B-01 error pattern is filtered out.
- `B-dup19765-variants.sql`: variants of the duplicate (run after creating ta/tb/tc/td).

Run from `bugprogress/scripts/`: `python3 B-fz2.py 101 60000 f1`.
