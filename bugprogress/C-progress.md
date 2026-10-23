# Hunter C: progress report (23-24 Oct 2026)

Method C: start from recent pgsql-bugs reports and recent bug-fix commits, reproduce
them, and mutate them into sibling code. Prefix `C-`.

## 1. Environment

| Item | State |
|---|---|
| master (cassert), `~/pgfuzz/install/master`, port 5433 | commit 126976a8 (23 Oct 2026). **Has the C-01 patch installed**, so it no longer shows C-01. |
| 18.6 release build, `~/pgfuzz/install/REL_18_STABLE`, port 5435 | built without libxml (setup_env.sh has no `--with-libxml` for it) |
| 18.6 cassert build, `~/pgfuzz/install/REL_18_cassert`, port 5436 | built by hunter C, with libxml; use this to show C-01 crashes |
| Newest master | `git fetch` on 23 Oct returned the same head, 126976a8 |

Setup problems fixed on the way: `apt-get` in setup_env.sh failed because `flex` and
`libicu-dev` were missing (installed by hand, then the script was re-run).
`scripts/../src/requirements.txt` does not exist, so the script ends with exit 1
after a successful build. psycopg was installed with pip.

Network: www.postgresql.org (list archive, message-ids) and www.mail-archive.com are
**blocked by this environment's network policy**. The pgsql-bugs list was read
through the GitHub mirror `MisterRaindrop/postgresql-github-mirror` (issues pages
1-5, 21 Sep - 23 Oct 2026, about 125 reports).

## 2. Confirmed bugs (reports written)

| ID | File | One line | Confidence |
|---|---|---|---|
| C-01 | `C-01-dependencies-duplicate-expression-assert.md` (+ `.sql`, `.patch`) | Two WHERE clauses on the same extended-statistics expression (`(b + 1) = 2 AND (b + 1) IN (2, 3)`, or `(c IS TRUE) AND (c IS TRUE)`) fail an incorrect Assert in `dependencies_clauselist_selectivity()`; backend crash on every cassert build; master and 18.6 affected, code from PG 14 | **High**: 3/3 on master, 3/3 on 18.6 cassert, root cause in source, patch passes all 239 regression tests. Assertion-only (release builds fine). Not filed yet. |

## 3. Candidates

### 3a. Valid but NOT new (already reported upstream by others)

Do not file these as ours. At most, add our extra evidence to the existing thread.

| # | Finding | Status / existing report |
|---|---|---|
| K1 | JSON_TABLE `PASSING` with an in-place-modified node gives an internal error: `SELECT * FROM (VALUES ('{"a":1}'::jsonb)) t(j), JSON_TABLE(t.j, '$' PASSING (NULL IS NULL) AS v COLUMNS (c bool PATH '$v')) jt;` gives `ERROR: unrecognized node type: 7` (XX000). The same happens with `IS TRUE`, `IS NOT UNKNOWN`, `ROW(NULL,1) IS NULL` and named arguments `f(x => NULL IS NULL)`. Master and 18.6. | Same root cause as **BUG #19786** (PASSING is analysed twice; the reply there says each analysis needs its own copy of the raw arguments). #19786 shows the subquery form; this XX000 form could be posted to that thread as extra evidence. |
| K2 | `ALTER TABLE parent ALTER COLUMN b TYPE bigint USING ((NULL IS NULL))::int` on a table with an inheritance child or partitions gives `ERROR: unrecognized node type: 7`. Master and 18.6. | **BUG #19756** (Sebastian Webber, with patch). Its report mentions this Const case. |
| K3 | Empty `oidvector` / `int2vector` cannot be read back through binary I/O: `COPY (SELECT ''::oidvector) TO ... (FORMAT binary)` and then COPY FROM fails with `invalid oidvector data` (22P03). Realistic case: binary COPY of `pg_proc.proargtypes` for zero-argument functions, or binary logical replication of such a column. `array_recv()` returns a 0-D array for zero items, but `oidvectorrecv()` / `int2vectorrecv()` insist on 1-D. Master and 18.6. | **BUG #5748 (2010)**, never fixed; Tom Lane doubted it was worth fixing then. Worth re-raising now that the same class was just fixed for tsquery (BUG #19778, commit 3c5a4a86): special-case an empty array in `oidvectorrecv` / `int2vectorrecv`. Credit the 2010 report. |
| K4 | Sorted GROUPING SETS return a value for a column outside the set, because `populate_isnull_array()` rewrites `tts_isnull[0..natts)` on every incremental deform and undoes the NULLs that `prepare_projection_slot()` forced. | **BUG #19785** (master/19 only). Hunter C grepped every other executor site that writes `tts_isnull` into a slot: all others use virtual or fully deformed slots, so no new site was found. |
| K5 | Qual pushdown past DISTINCT / window PARTITION BY when a function distinguishes "equal" values (numeric scale, float -0) | Acknowledged in the comment of `expression_has_grouping_conflict()` (commit 44fb59fc); reported as BUG #19649, #19713, #19722. |
| K6 | "corrupt MVNDistinct entry" for `GROUP BY ..., ROLLUP(expr)` with ndistinct statistics; "expression not found in statistics object" for MCV statistics with a boolean domain column | **BUG #19772** and **BUG #19789**; our extended-statistics fuzzer hit both again (no new information). |

### 3b. Doubtful (probably not accepted)

| # | Finding | Why doubtful |
|---|---|---|
| D1 | `sign('NaN'::float8)` returns 0, while `sign('NaN'::numeric)` returns NaN | Behaviour dates from the original code. The docs say the result is -1, 0 or +1 and say nothing about NaN. Upstream would probably call it intended or not worth changing. |
| D2 | Binary send of an xml value drops a plain `<?xml version="1.0"?>` declaration (the text cast keeps it) | Not a bug: `xml_out_internal()` / `print_xml_decl()` omit a version-1.0 declaration with no encoding or standalone attribute by design, for text output too. Recorded so nobody re-checks it. |

### 3c. Untested ideas (seeds for the next session)

| # | Idea | Seed |
|---|---|---|
| U1 | first_value / last_value / nth_value with `EXCLUDE GROUP`, `EXCLUDE CURRENT ROW` and `GROUPS` / `RANGE` frames, compared against `array_agg(...) OVER w` or a Python reference. The EXCLUDE TIES case is BUG #19731/#19732 (patch v4 pending); the other exclusion modes go through the same `WinGetFuncArgInFrame` code. | #19731, #19732 |
| U2 | JIT tuple deforming (`llvmjit_deform.c`) with the GROUPING SETS case of #19785 (`SET jit = on, jit_above_cost = 0`; needs an LLVM build, ours has none) | #19785 |
| U3 | Other places that analyse the same raw parse tree twice (the class of #19756 / #19786): `transformNullTest`, `transformBooleanTest` and `NamedArgExpr` are modified in place. 96 statement templates × 10 expressions found only K1 and K2. Not yet covered: ecpg, PL/pgSQL `RETURN QUERY` / cursors, rules, `CREATE TABLE ... (LIKE ...)` with expressions | #19756, #19786 |
| U4 | Siblings of BUG #19784 (estimator code running before baserels exist): Tom Lane is changing `examine_variable()`; re-test after his commit with other estimators (`scalararraysel`, `estimate_num_groups`) on MinMaxAgg tlists and in index expressions | #19784 |
| U5 | Binary-recv round trip extended to contrib types (hstore, ltree, cube, seg, citext, pg_trgm) and to multidimensional or empty arrays of user types | #19778 |

## 4. Checked, no bug found (with counts)

- **Binary I/O round trip** (`binrt.py`): ~140 edge values over 50 core types (tsquery, tsvector, jsonb, jsonpath, numeric NaN/±Inf/-0, float, interval/date/timestamp infinity, ranges/multiranges, arrays with odd bounds, inet/cidr, geometric types with NaN, xml, snapshots, regtype, "char", tid, xid8). Only K3 and D2, both on master and 18.6.
- **numeric vs float8** (`numfloat.py`), sibling of commit 94e1385e (numeric log): 14 unary and 13 binary functions over 13 edge values (2379 cases). Only differences: the log(base, Infinity) cases fixed by 94e1385e (18.6 still has the old answer, as intended), documented float underflow errors, round-half-even differences, and D1.
- **Aggregates as window functions** (`winagg.py`), sibling of 41180127 (jsonb_object_agg in windows): 64 aggregates (numeric/float/interval with NaN/Infinity, bool, bit, json/jsonb aggregates including the strict/unique variants, range_agg, xmlagg, regression aggregates, FILTER) × 8 frame shapes (moving ROWS frames that use inverse transition functions, RANGE, GROUPS, EXCLUDE CURRENT ROW) × 3 data seeds, compared against correlated subqueries. All equal on master.
- **Raw-tree double analysis** (`raw2x.py`): 96 statement contexts (BETWEEN, IN, CASE, GROUPING SETS, all SQL/JSON constructors, XMLTABLE, MERGE, ON CONFLICT, CALL with named args, policies, triggers, generated columns, partition bounds, ALTER TABLE on inheritance and partitioned tables, ...) × 10 expressions. Only K1 and K2.
- **Inheritance DDL recursion** with a child whose columns are in a different order (ADD COLUMN DEFAULT, stored and virtual generated columns, SET EXPRESSION, ADD CHECK): results and catalog expressions correct.
- **Extended statistics** (`xstats.py`, `xstats2.py`): 26 seeds × 4000 EXPLAINs over random statistics objects (all kinds, expressions, domains, partitioned/inheritance parents and leaves) and about 100 clause shapes. Found C-01 and re-hit K6; nothing else after C-01 was patched.
- **Code reading, no bug:** callers of `eval_const_expressions(NULL, ...)` that might miss `fix_opfuncids()` (sibling of a14041d4, the COPY WHERE fix; all other callers either call it or pass the result through `expression_planner`); functions that write into the caller's `fcinfo->args` (sibling of e355089a, jsonb_set_lax; none left in utils/adt); CASE/COALESCE/NULLIF reduction relabelling (d8ce0050 covers all three).

## 5. Scripts

In the hunter-C scratchpad of the session (not committed): `binrt.py`, `numfloat.py`,
`winagg.py`, `xmlrt.py`, `raw2x.py`, `xstats.py`, `xstats2.py`. They can be added to
the repository if wanted.
