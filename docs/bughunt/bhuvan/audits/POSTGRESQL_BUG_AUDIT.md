# PostgreSQL correctness audit (23 October 2026)

All artifacts referenced below are in [`bughunt/audit/`](bughunt/audit/).
Nothing was sent to any PostgreSQL list or tracker.

## A. Executive summary

| Item | Value |
|---|---|
| Target | PostgreSQL `master` (20devel) at **`896246ea10cb9d20f69d0442223ce5fa9b365636`** (2026-10-23, "Remove faulty Asserts added by 1999fe227") |
| Also tested | `REL_19_STABLE` at `015f4c9fc35f91a1ab46bafab05a3686cfe09d46` (reports **19rc1**); 18.6 release build (`REL_18_STABLE` `d7938ff3`) |
| Build | `--enable-cassert --enable-debug --with-libxml --without-icu`, `CFLAGS=-O1 -g -fno-omit-frame-pointer` (18.6: `-O2`, no asserts) |
| Environment | WSL2 Ubuntu 24.04, Linux 6.18.33.2, gcc 13.3.0, 12 cores; disposable clusters on ports 5460 (master), 5461 (18.6), 5462 (19rc1); separate git worktrees under `~/audit/src/`, upstream trees untouched |
| Areas | A (planner/executor), B (partitioning, indexes, plan cache), C (data types, JSON, serialization) |
| Hypotheses examined | **22** |
| Confirmed, apparently new | **1** (AUDIT-F1, below) |
| Disproved | **15** |
| Already known (duplicates of open reports) | **3** (BUG #19735, BUG #19746, the "hashed SubPlan referenced twice" thread) |
| Inconclusive / insufficiently investigated | **1** reviewed only, **2** not investigated |
| Crashes / assertion failures seen | 0 (server logs of all three clusters scanned: TRAP=0, PANIC=0, signal=0) |

The confirmed defect: **PostgreSQL 19's NOT IN → anti-join conversion returns rows that
NOT IN must reject** when the parser applies an implicit cast to the sub-select's output column
and that cast can return NULL for a non-null input. It is a wrong-result regression from commit
`383eb21ebf` (2026-03-12), present in 19rc1 and master, absent in 18.6. It needs a user- or
extension-defined implicit cast with that property; none of the 69 built-in implicit casts has it.
A two-part fix (a check plus a regression test) passes the full core regression suite (239/239).

Test volume run in this session (all on master unless noted):

| Campaign | Volume | Mismatches |
|---|---|---|
| JSON_TABLE NESTED/PLAN vs lateral reference (`jtfuzz.py`) | 18,300 cases (6 × 3,000 + 300) | 0 |
| Partition pruning: plain table vs plan-time vs generic-plan vs pruning off (`ptfuzz.py`) | 2,934 random partitioned tables, 44,010 predicates | 0 |
| btree index scan / index-only / bitmap vs seqscan (`ixfuzz.py`) | 2,400 tables, 57,600 queries | 0 |
| Hash opclass invariants (`hashcheck.py`) | 44 types, about 330 literals | 0 |
| json vs jsonb constructor equivalence (`jsoneq.py`) | 1,450 comparisons | 4 (all known BUG #19735) |
| interval text round trip, 4 IntervalStyles (`intervalrt.py`) | 12,108 checks | 1 (known BUG #19746) |

Earlier campaigns by the team (`bughunt/LOG.md`, not re-run here) add about 320,000 grammar-fuzzer
test cases, 214,000 cross-version join queries and 160,000 TLP/NoREC checks, with no new bug.

## B. Findings

### AUDIT-F1: NOT IN → anti-join conversion ignores an implicit cast on the sub-select side

**Affected code (master `896246ea`)**

| File | Function | Lines |
|---|---|---|
| `src/backend/optimizer/plan/subselect.c` | `convert_ANY_sublink_to_join()`: the NOT IN gate | 1383–1386 |
| `src/backend/optimizer/plan/subselect.c` | `sublink_testexpr_is_not_nullable()` | 1501–1601 |
| `src/backend/optimizer/util/clauses.c` | `query_outputs_are_not_nullable()` | 2177–2302 |
| `src/backend/parser/parse_expr.c` | `transformSubLink()`: builds `PARAM_SUBLINK` Params and the test expression | 1965–2010 |

**Root cause.** Commit `383eb21ebf` ("Convert NOT IN sublinks to anti-joins when safe") states the
invariant: the conversion is safe if "neither side of the comparison can yield NULL" and the operator
cannot return NULL for non-null inputs. The code checks three things:

1. the operator belongs to a btree or hash opfamily (`op_is_safe_index_member`);
2. each **outer** operand is non-nullable (`expr_is_nonnullable(..., NOTNULL_SOURCE_HASHTABLE)`);
3. each **sub-select output column** is non-nullable (`query_outputs_are_not_nullable`).

The inner operand of the comparison is not the sub-select output column. It is the expression that
`transformSubLink()` built over the `PARAM_SUBLINK` Param, and operator resolution may wrap that Param
in an implicit coercion to the operator's input type (visible in EXPLAIN as `(s.i)::text`).
`sublink_testexpr_is_not_nullable()` takes only `linitial(opexpr->args)` (the outer side) and never
looks at `lsecond(opexpr->args)`. A cast function may return NULL for a non-null input. The comparison
then yields NULL, so NOT IN yields NULL and the row must be rejected; the anti-join instead treats the
comparison as "no match" and keeps the row. The same gap exists in the multi-column (AND/OR of
OpExprs) and RowCompareExpr branches, and for correlated (LATERAL) sub-selects.

**Preconditions.** Both sides provably NOT NULL; an implicit cast (`CREATE CAST ... AS IMPLICIT`)
that the parser applies to the sub-select side and that returns NULL for some non-null input. All 69
built-in implicit casts use internal C functions that never return NULL for non-null input
(`probes/a1_casts.sql`), so a user- or extension-defined cast is required.

**Minimal reproducer** (`probes/F1_repro.sql`):

```sql
CREATE FUNCTION i2t(int) RETURNS text IMMUTABLE STRICT LANGUAGE sql
  AS $$ SELECT CASE WHEN $1 <> 0 THEN format('%s', $1) END $$;   -- NULL for 0
CREATE CAST (int AS text) WITH FUNCTION i2t(int) AS IMPLICIT;

CREATE TABLE o (t text NOT NULL);
CREATE TABLE s (i int NOT NULL);
INSERT INTO o VALUES ('1');
INSERT INTO s VALUES (0);

SELECT t, t NOT IN (SELECT i FROM s) AS not_in FROM o;   -- ground truth: '1' | NULL
SELECT t FROM o WHERE t NOT IN (SELECT i FROM s);        -- must return 0 rows
```

**Expected:** 0 rows ('1' = i2t(0) is '1' = NULL, so NOT IN is NULL and WHERE rejects the row).
**Actual (master, 19rc1):** 1 row, `1`, under a `Merge Anti Join` with `Merge Cond: (o.t = ((s.i)::text))`.
18.6 keeps `Filter: (NOT (ANY (t = ((hashed SubPlan 1).col1)::text)))` and returns 0 rows.

**Evidence from repeated runs** (`evidence/F1_evidence.txt`: fresh database per run, 3 runs per server):

| Variant | master 896246ea | 19rc1 015f4c9f | 18.6 |
|---|---|---|---|
| ground truth (`t NOT IN (...)` in target list) | NULL ×3 | NULL ×3 | NULL ×3 |
| single column, merge anti join | 1 row ×3 (wrong) | 1 row ×3 (wrong) | 0 rows ×3 |
| `enable_mergejoin=off` (hash anti join) | 1 row ×3 (wrong) | 1 row ×3 (wrong) | 0 rows ×3 |
| also `enable_hashjoin=off` (nested loop) | 1 row ×3 (wrong) | 1 row ×3 (wrong) | 0 rows ×3 |
| multi-column `(t, k) NOT IN (SELECT i, k ...)` | 1 row ×3 (wrong) | 1 row ×3 (wrong) | 0 rows ×3 |
| correlated `t NOT IN (SELECT s2.i ... WHERE s2.k = o2.k)` | 1 row ×3 (wrong) | 1 row ×3 (wrong) | 0 rows ×3 |

Adding `OFFSET 0` to the sub-select does not avoid the bug: the sub-select is still converted, as a
subquery RTE.

**Affected versions.** Introduced by `383eb21ebf` (2026-03-12, before the REL_19 branch point of
2026-06-29). Reproduced on REL_19_STABLE (19rc1) and master. 18.6 and earlier never convert NOT IN to
an anti-join. Later commits to this code (`363af93bdd` invalid NOT NULL constraints, `0d99579320`
upper-level Vars, `31c002aa89` refactor) do not touch the inner operand.

**Duplicate search** (2026-10-23):

* Full pgsql-bugs index, May–October 2026: 1,954 messages, 412 threads
  (`pgsql-bugs-threads-2026-05-to-10.tsv`). No report about NOT IN, anti-joins and casts. BUG #19734
  ("NOT IN type resolution differs for outer Vars") is about NOT IN with a *value list* and is unrelated.
* postgresql.org site search (365 days, all lists) for `NOT IN anti join cast`,
  `NOT IN antijoin coercion NULL`, `sublink_testexpr_is_not_nullable`,
  `query_outputs_are_not_nullable` and `NOT IN anti-join wrong result`. The hits were read:
  * design thread "Convert NOT IN sublinks to anti-joins when safe" (23 messages, Feb–Mar 2026):
    operator NULL behaviour and operand nullability are discussed; casts and coercions are not;
  * "Wrong results: NOT IN to anti-join with an upper-level Var in the sub-select's output"
    (Jul–Aug 2026, fixed by `0d99579320`): a different hole;
  * "Prove a NOT IN's left-hand expressions non-nullable from quals" (open, Jun–Aug 2026): about the
    **outer** side only. Its `RelabelType` loop strips the left-hand expression;
  * "var_is_nonnullable() fails to handle invalid NOT NULL constraints" (fixed by `363af93bdd`).
* Git history of `sublink_testexpr_is_not_nullable` and `query_outputs_are_not_nullable` since `383eb21ebf`.

**Outcome:** no existing report or fix found.

**Proposed fix** (`bughunt/audit/0001-NOT-IN-antijoin-reject-coerced-inner-arg.diff`, kept as an
uncommitted diff in worktree `~/audit/src/pg-fix`). It requires each inner operand to be the bare
`PARAM_SUBLINK` Param, optionally under a binary `RelabelType`, in all three branches of
`sublink_testexpr_is_not_nullable()`:

```c
static bool
sublink_inner_arg_is_param(Node *arg)
{
	while (arg && IsA(arg, RelabelType))
		arg = (Node *) ((RelabelType *) arg)->arg;

	return arg && IsA(arg, Param) &&
		((Param *) arg)->paramkind == PARAM_SUBLINK;
}
```

Validation:

* `make check` with the patch: **All 239 tests passed** (`evidence/make-check-fix.txt`). Before the
  expected file was updated, the only difference was the new test's output. No existing plan changed.
* The new regression test (in `subselect.sql`, inside the existing NOT IN block) returns the correct
  0 rows with the fix. The same statements return the wrong 1 row on unpatched master and 19rc1, so
  the test detects the bug.
* Trade-off: the fix also stops the conversion when the sub-select side needs a *built-in*
  non-binary cast (for example `numeric_col NOT IN (SELECT int_col ...)`). The catalog cannot tell
  that a cast never returns NULL, so this seems the right conservative choice. A committer may prefer
  another way.

**Impact and severity.** Wrong query results: rows are silently returned that NOT IN semantics
exclude. No crash, no assertion failure, no data modification, no privilege or security effect was
observed. **Likelihood is low**, because the trigger needs a NULL-returning implicit cast.
**Severity: low to moderate.** It is a correctness regression in a major version still at RC stage,
where a small fix is cheap.

## C. Negative and inconclusive results

Code review means the hypothesis was refuted by reading the code path. Tested means it was refuted
by running queries.

| ID | Hypothesis | Method | Result |
|---|---|---|---|
| A-1 | `var_is_nonnullable()` trusts NOT NULL wrongly for NO INHERIT / inheritance parents / NOT VALID / partitioned virtual generated columns | code review (`clauses.c` 4851–4985, `plancat.c` 170–179, 689–754) | disproved: each case is handled (`has_subclass`, `ATTNULLABLE_VALID`, fixes `363af93bdd` and `d8444163d2`) |
| A-2 | catalog expressions (index expressions and predicates, CHECK, ON CONFLICT) are const-folded with a real `root` while still at `varno = 1`, so NOT NULL folding looks up the wrong RTE | code review (`plancat.c` 434–453, 1050–1057, 1149–1159, 1566–1579) | disproved: `ChangeVarNodes` runs before `eval_const_expressions` everywhere |
| A-3 | `expression_planner_with_deps()` passes a dummy root (`parse = NULL`), so `var_is_nonnullable` could dereference NULL | code review | disproved: the only caller (PL/pgSQL cast cache) has no Vars |
| A-4 | FULL→ANTI reduction (master-only) proves non-nullness from the join's own ON clause, which does not hold for unmatched rows | code review (`prepjointree.c` 3652–3690) | disproved: ON quals are explicitly excluded for FULL joins |
| A-5 | the redundant-IS-NULL stripping runs before nullingrel removal for a partially reduced FULL join, dropping a needed qual | code review (`prepjointree.c` 3345–3383, 3431–3444) | disproved: partial nullingrel removal comes first |
| A-6 | the system-column shortcut in `forced_null_var_is_attnotnull()` runs before the RTE-kind check | code review | disproved: system-column Vars exist only for relation RTEs |
| A-7 | EXISTS→ANY hashed alternative changes EXISTS's two-valued result under NOT or OR | code review (`subselect.c` 259–330, 1971–2179) | disproved: long-standing code, protected by `unknownEqFalse` |
| A-8 | NOT-NULL-based constant folding (`DistinctExpr`, `COALESCE`, `ROW() IS NULL`, `BooleanTest`) mis-handles a case | code review (`clauses.c` 3075–3135, 3823–3870, 4030–4220) | no defect found; not exhaustively tested |
| **A-9** | **NOT IN→anti-join ignores a NULL-producing coercion on the inner operand** | tested | **confirmed: AUDIT-F1** |
| A-10 | JSON_TABLE NESTED PATH / PLAN (master-only `86ab7f4c72`, plus the re-evaluation optimization `6d8fd5a881`) gives rows that differ from the standard semantics | differential fuzz: 18,300 cases, explicit / DEFAULT / no plan, ORDINALITY, lax unwrapping, JSON null items | disproved for the space covered. The first 35 mismatches were a column-order bug in my own oracle, found and fixed before the campaign |
| A-11 | `ALTER ... SET EXPRESSION` on a virtual generated column does not re-check its NOT NULL, so NOT-NULL folding gives wrong results | tested (`probes/a18_vgen_setexpr.sql`) | disproved: rejected with "contains null values" |
| A-12 | outer-query virtual generated columns are still unexpanded when `pull_up_sublinks` uses the HASHTABLE source | code review (`planner.c` 871 vs 886) | disproved: they are expanded first |
| A-13 | hashed SubPlan state is reused across references or rescans | archive | **known**: thread "Wrong results: hashed SubPlan referenced twice after OR-qual extraction..." (2026-10-01), patch v2 under review, plus an EPQ sibling found by Alexandra Wang. Not pursued |
| A-14 | grouping-expression references in sub-selects (`415100aa62`) mis-match under grouping sets | code review only | inconclusive: parser-side, failures would more likely be errors than wrong rows. Not tested |
| B-1 | partition pruning drops or keeps the wrong partitions (multi-column RANGE with MINVALUE/MAXVALUE/DEFAULT, LIST with NULL, HASH, sub-partitions, int2/int8 constants, IN/ANY/ALL/BETWEEN/NOT) | differential fuzz: 2,934 tables, 44,010 predicates × {plain, plan-time, generic plan, pruning off} | disproved for the space covered. A first run gave false mismatches because the parallel workers shared one database (my harness bug, fixed with a database per worker) |
| B-2 | btree index scans disagree with seqscan (row compares, SAOP with NULL elements, skip scan, redundant/contradictory keys, ASC/DESC, NULLS FIRST/LAST, both directions) | differential fuzz: 2,400 tables, 57,600 queries × {seq, index, index-only, bitmap} | disproved for the space covered |
| B-3 | cached plans built on NOT NULL proofs are not invalidated after `DROP NOT NULL`, or after an inheritance child with NULLs is added | tested (`probes/b3_plancache_notnull.sql`): generic plan, inheritance, SQL function, PL/pgSQL | disproved: re-planned correctly in every case |
| C-1 | a hash opclass breaks "x = y ⇒ hash(x) = hash(y)", the salted variant, the documented "low 32 bits of `hash_ext(x,0)` = `hash(x)`", or cross-type agreement in `integer_ops` / `float_ops` / `text_ops` | `hashcheck.py`: 44 types (numeric scales and NaN, ±0, interval month/day forms, jsonb numerics, ranges and multiranges, records, arrays, ...) | disproved: 0 violations |
| C-2 | json and jsonb constructors (`to_json`, `*_agg`, `*_object_agg[_strict/_unique]`, `JSON_OBJECT`, `JSON_ARRAY`, `JSON_OBJECTAGG`, `JSON_ARRAYAGG`, `JSON_SCALAR`) disagree on SQL NULL vs JSON null | `jsoneq.py`: 58 values × 25 constructor pairs | **known**: 4 differences, all JSON `null` dropped by the jsonb `ABSENT ON NULL` / `*_strict` paths, exactly BUG #19735 (the thread already lists all four variants) |
| C-3 | interval output does not read back under some IntervalStyle | `intervalrt.py`: 12,108 checks, exact field comparison | **known**: 1 failure (`-2147483648 days` in `postgres_verbose`), already in BUG #19746 |
| C-4 | pg_dump/restore round trip of newer syntax | — | **not investigated** (time) |
| C-5 | nondeterministic collations (hash, pruning, uniqueness) | — | **not investigated**: built `--without-icu`, so no nondeterministic collations exist. Many reports already exist (#19633, #19641, #19645, #19646, #19681) |

Counts: 22 hypotheses = 1 confirmed + 15 disproved (A-1–A-8, A-10–A-12, B-1–B-3, C-1) + 3 known
duplicates (A-13, C-2, C-3) + 1 inconclusive (A-14) + 2 not investigated (C-4, C-5).

**Limitations.**

* The local clone is shallow (history starts at `d80b022501`, 2026-03-01), so older history was not
  available offline. This does not affect F1: the introducing commit (`383eb21ebf`, 2026-03-12) is
  inside the window.
* The pgsql-hackers archive was not indexed in full; only targeted searches and threads were read.
* The commitfest application was not checked.
* TAP tests were not run (built with `--enable-tap-tests=no`).
* No concurrency or isolation testing was done; no race hypothesis came up that would need it.
* Fuzz campaigns cover only the generated shapes; "disproved" means no counterexample in that space.

## D. Proposed upstream report (draft, **not sent**)

> **Subject:** Wrong result from NOT IN converted to anti-join when the sub-select output is implicitly cast
>
> **PostgreSQL version:** 19rc1 (REL_19_STABLE 015f4c9fc3) and master (896246ea10). 18.6 is not affected.
> **Platform:** x86_64 Linux (Ubuntu 24.04, gcc 13.3), assert-enabled builds
>
> Since 383eb21ebf, NOT IN is converted to an anti-join when both operands are proven non-nullable
> and the operator is a btree/hash opfamily member. The proof checks the outer operands and the
> sub-select's output columns, but not the inner operand of the comparison itself. Operator
> resolution may wrap the sub-select's output Param in an implicit cast, and a cast function can
> return NULL for a non-null input. Then NOT IN yields NULL (row rejected), but the anti-join keeps
> the row.
>
> ```sql
> CREATE FUNCTION i2t(int) RETURNS text IMMUTABLE STRICT LANGUAGE sql
>   AS $$ SELECT CASE WHEN $1 <> 0 THEN format('%s', $1) END $$;
> CREATE CAST (int AS text) WITH FUNCTION i2t(int) AS IMPLICIT;
> CREATE TABLE o (t text NOT NULL);
> CREATE TABLE s (i int NOT NULL);
> INSERT INTO o VALUES ('1');
> INSERT INTO s VALUES (0);
>
> SELECT t, t NOT IN (SELECT i FROM s) FROM o;        -- 1 | NULL
> SELECT t FROM o WHERE t NOT IN (SELECT i FROM s);   -- expected 0 rows
> ```
>
> **Expected:** 0 rows. **Actual:** 1 row (`1`), via `Merge Anti Join ... Merge Cond: (o.t = ((s.i)::text))`.
> 18.6 returns 0 rows using a hashed SubPlan. The result is the same with hash and nested-loop anti
> joins, for the multi-column form `(t, k) NOT IN (SELECT i, k ...)`, and for a correlated sub-select.
>
> A possible fix is to require, in `sublink_testexpr_is_not_nullable()`, that each inner operand be
> the bare PARAM_SUBLINK Param (optionally under RelabelType). A patch with a regression test is
> attached; `make check` passes. It also gives up the conversion when a built-in non-binary cast is
> needed on the sub-select side, which seems acceptable since we cannot prove such casts never
> return NULL.

## Appendix: reconnaissance and how to reproduce

* **Repository.** This project is not a PostgreSQL checkout. PostgreSQL sources live in WSL under
  `~/pgfuzz/src/` (team trees, not modified) and `~/audit/src/` (this audit: `pg-master` and `pg-19`
  are detached worktrees at the commits above; `pg-fix` is the fix worktree).
* **Previous work in this project.** It was read first (`bughunt/HANDOFF-2026-10-18.md`,
  `LOG.md`):
  * BUG #19768 (JSON_TABLE collations): filed by the team.
  * candidate 2: known BUG #17731.
  * grammar-hunt crash: known BUG #19766.
  * extended-stats non-finite note: under an existing hackers thread.
* **Duplicate index.** `bughunt/audit/pgsql-bugs-threads-2026-05-to-10.tsv` has one row per
  thread: first message date, message count, subject, link, authors. Tools to rebuild and query it
  are in `archive-tools/`:
  * `paginate.py` and `threads.py` build the index;
  * `thread.py`, `print_msg.py` and `search.py` read threads and query the site search;
  * `check_*.sh` are the exact duplicate checks run for F1, #19735, #19746 and the hashed-SubPlan thread.
* **Upstream fix stream.** Since 2026-10-15 master had 65 commits. The planner fixes (Richard Guo,
  Tom Lane), deparse fixes (Henson Choi) and type input/output hardening (Tom Lane) show where other
  people are finding bugs. Those clusters were deprioritized as crowded unless a new invariant was in
  hand.
* **Re-run F1:** start any server, then `psql -X -f bughunt/audit/probes/F1_repro.sql`.
* **Re-run the fuzzers:** `python <fuzzer>.py PORT SEED N` with psycopg 3. `ptfuzz.py` and
  `ixfuzz.py` create their own database per seed.
