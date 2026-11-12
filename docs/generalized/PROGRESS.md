# Progress log (generalized fuzzer)

## Open decisions (left blank on purpose; the owner fills them in during reviews)
- Venue: TBD
- Paper authorship and AI-use statement: TBD
- Anonymous artifact mirror: TBD
- Final paper title (working title in PLAN.md section 1): TBD
- LLM model and API key: only needed for Phase L (LLM extension, moved to the end by the owner): TBD
- Extra machines for evaluation (this one has 4 cores; the session's disk allowance is ~40 GB, about 13-17 GB free
  with one engine build at a time): TBD
- **Contribution policies of the three projects (read before filing):** DuckDB `AI_POLICY.md` allows AI-assisted code
  but requires issues, PR descriptions and replies to be written by the human contributor in their own words, and
  closes contributions from autonomous agents; DataFusion's AI policy requires the author to understand the whole PR and
  answer reviews personally, and limits non-committers to 3 open PRs; Turso's PR template has a required
  "Description of AI Usage" section. The packages' `issue.md` / `pr.md` are therefore notes to rewrite in your own
  words, and Turso's AI-usage section is left for you (`<!-- TO FILL BY THE OWNER -->`). Which bugs to file and when,
  and what to write in Turso's AI section: owner's decision.

## Blocked
- (8 Nov) Builds are allowed now: DuckDB `main`, DataFusion `main` (`datafusion-cli`, sqllogictests) and Turso `main`
  (`tursodb`, sqltest runner) were built from source this session. Resolved: the earlier "cargo build blocked" items.
- Building SQLite trunk was not retried yet this session (C5 needs it; next).
- GitHub GraphQL (`gh search`) is not available; the REST search API works and was used for duplicate searches.

## Bug packages (filed: T-05, D-01, DF-01 by the owner; links in docs/bughunt/filed.yaml)
Status after re-checking each bug on the engine's newest development code built from source (8 Nov 2026):

| Bug | Engine | Reproduces on main? | Fix written and tested? | Package |
|---|---|---|---|---|
| D-01 min/max over nested value with subquery | DuckDB | yes (d4eea3f208) | yes (`fix.patch`, new .test, fast unittest suite passes) | `docs/bughunt/duckdb/D-01-minmax-nested-subquery/` |
| D-02 outer join / MERGE ON with two subqueries | DuckDB | **no: fixed upstream by 57a6875edf (PR #28246, issue #28156)**, confirmed by reverting it | not needed | `docs/bughunt/duckdb/D-02-outer-join-two-subqueries/` (do not file) |
| DF-01 UPDATE/DELETE with repeated expression (`__common_expr`) | DataFusion | yes (bc86321); also WHERE of UPDATE/DELETE | yes (`fix.patch`, new .slt cases, all 546 .slt files + clippy pass) | `docs/bughunt/datafusion/DF-01-update-coalesce-common-expr/` |
| DF-02 scalar subquery in VALUES | DataFusion | yes (bc86321); also INSERT ... VALUES | yes (`fix.patch`, new .slt cases, all 546 .slt files + clippy pass) | `docs/bughunt/datafusion/DF-02-values-scalar-subquery/` |
| T-05 percentile with expression argument | Turso | yes (9b71df9ab) | yes (`fix.patch`, new .sqltest; full sqlite-sqltests corpus 12700 passed) | `docs/bughunt/turso/T-05-percentile-expression-argument/` |
| T-02 window fn over DATE() twice in ORDER BY (panic) | Turso | **no: fixed upstream by merge 8f1f6ee83 "register ORDER BY window functions only for terms that are kept" (16 Oct 2026), found by bisect** | not needed | `docs/bughunt/turso/T-02-window-arg-call-order-by-twice/` (do not file) |
| T-01 FULL JOIN on INTEGER PRIMARY KEY rejected | Turso | **no: fixed upstream by 44fe44520 "core: implement SQLite-style right and full joins" (merge 2b9184f8d, 7 Oct 2026; parent still fails, merge works)** | not needed | `docs/bughunt/turso/T-01-full-join-rowid-equality/` (do not file) |
| T-08 aggregate in `IN (SELECT ...)` with a window function (misuse error; panic for median) | Turso | yes (38b7d9de1, 12 Nov 2026) | yes (patch, new .sqltest; window/agg/subquery corpora 1399 passed, sqlite-sqltests 12726 passed except the 2 big-db disk tests, turso+shared 3661 passed) | `latestbugs/T-08-turso-window-aggregate-in-subquery/` (**ready to file**) |

Filing order suggested in each `steps.md`: issue first, then the PR. Ready to file: D-01, DF-01, DF-02, T-05
(DataFusion: one PR at a time on a first contribution).

## Session log

## 2026-11-12: T-08 (Turso), BUG #19826 v4, hunt on newest code

Later the same day:

- Upstream states (checked 12 Nov): PostgreSQL BUG #19802 fixed (`7a5559a6`, Tender Wang /
  Dean Rasheed, back-patched to 15) -> seven of nine PostgreSQL bugs fixed. DuckDB PR #28552
  approved by a maintainer (auto-merge on, labelled for the 2.0 backport). Turso PR #11595: a
  reviewer found a GROUP BY case, the owner added a test. DataFusion PR #27236 validated by a
  contributor. `main` (course submission) updated: paper, README, completion/, slides, guide.
- hunt_main triage, all verdicts in `latestbugs/README.md`: DuckDB nightly internal errors are
  #27720 / #27983 (already reported); DataFusion 55.0.0: `round(decimal, 2)` comparison error
  fixed on main by #23232, UNION nullability by #24244, interval range frames reported as #24915;
  Turso: the 466 differences are T-05 (filed) and the bare-column issue #5545. No new bug.
- Tool: known bugs match on SQL (`sql_regex`), so filed bugs stop dominating Turso campaigns;
  triage no longer crashes on non-PostgreSQL wrong results (plan-variant localization is
  PostgreSQL only).
- Rule kernels from engine test suites (`kernels --from-suite`), kernel transfer
  (`--transfer-from`), memory cap for mining. Three probe bugs fixed: (1) the DuckDB rule probe
  replaced a test case's own `SET disabled_optimizers` instead of adding to it, so every rule
  looked as if it fired (47 of 48 rules for one query); (2) a failing setup statement made the
  whole probe fail; (3) on DuckDB a failed reset skipped the ROLLBACK and left later probes in
  an aborted transaction. Kernel numbers before these fixes are void; the corpora in
  `src/corpus/kernels/` are re-mined.
- A fourth probe bug: the SQLite probe reset a test case's own `PRAGMA automatic_index` /
  `reverse_unordered_selects` to the defaults after the first rule, so one such PRAGMA made 29 of
  30 rules look as if they fired (the plain campaign arm showed "30 rules", 12 of them exactly
  12 times). Fixed; SQLite kernels re-mined.
- Kernels (after all fixes): SQLite: grammar fires 16 of 30 rules; 17 rules with kernels (33
  kernels), 136 pairs, 123 co-fire, 400 seeds, 0 violations. DuckDB: grammar 28 of 48, its
  optimizer tests 5 more; 31 rules with kernels (60), 464 pairs, 364 co-fire, 1283 seeds, 0
  violations. Transfer SQLite -> DuckDB: 29/33 run, 13 DuckDB rules, none new; DuckDB -> SQLite
  5/60 run. DataFusion: suite mining killed by a test that exhausts memory in-process (Rust
  aborts on allocation failure); grammar-only mining instead. Panics seen in DataFusion 55.0.0 on
  its own `main` tests (`aggregate_skip_partial`, `array_concat`) are fixed on main: not bugs.
- Kernel campaigns (2 arms x 3 trials x 15 min): DuckDB rule pairs 307 -> 386 (A12 1.00,
  p 0.10), rules 31 -> 33, 3 rules only with kernels, similar test-case counts; SQLite rule
  pairs 86 -> 182, rules 17 -> 21, but twice the test cases. One TLP false positive (QUALIFY with
  a window function) fixed. `docs/generalized/results/rq8_kernels_2026-11-12.md`.

- BUG #19826 (PostgreSQL, main branch package): reviewed Tom Lane's v3 on master b0496e3
  (243/243 regression tests); v4 fixes the commonX/commonY entries of the old direct
  `float8_regr_combine()` test (its other numbers are real states of `regr_test`) and adds
  overflow tests. The owner sent the reply with v4 (`docs/bughunt/new/` on `main`).
- Turso lead from the 11 Nov hunt (panic "aggregate called in scalar context", failure
  3308362ffef6) reduced by hand: an aggregate in `IN (SELECT ...)` in a query with a window
  function. Built-in aggregates are wrongly rejected as misuse, extension aggregates panic.
  Still on main 38b7d9de1. Cause in `core/translate/window.rs` (`rewrite_terminal_expr` passes
  `contains_aggregates = false` for subquery expressions); fixed, test added, corpora pass.
  Open PR #11597 only changes the panic into the wrong error. Package: `latestbugs/T-08-*`.
- `TursoDriver` now reports the version of the pyturso it actually loads (0.9.0rc5 from
  `/root/arbor/pyturso-main`, was misreported as the pip 0.8.3).
- Hunt on newest builds (`results/hunt_main`) crashed when a Rust build filled the disk;
  restarted. Build Turso with `CARGO_INCREMENTAL=0` and delete `target/release` after the
  wheel is built: the session's disk allowance is small.

## 2026-11-11: branch `generalised-improved` (new techniques, hunt on newest code)
- New branch `generalised-improved`; hand-over for the next session: `docs/generalized/NEXT.md`.
- Literature check (web search): SQL Server rule-testing framework (SIGMOD 2009) covers rules and rule pairs but reads
  rule patterns from the optimizer; ARG (ASE 2025) abstracts single rules from rewriter source. No prior work found that
  learns a rule's trigger by reduction or composes triggers with a built-in oracle.
- Rule kernels (`pgfuzz kernels`): mining by tree reduction under "the rule still fires" (median 260 -> 57 tokens on
  SQLite), 6 composition templates with a composition oracle, 3 identity grafts. 1,239 composed seeds on SQLite, DuckDB,
  DataFusion: no violation at default settings.
- State-restoration oracle (tables and row counts must be unchanged after ROLLBACK). Found Turso T-06 on 0.8.3
  (runtime error ends the transaction; later INSERT commits). Also T-07 (correlated subquery in HAVING reads NULL).
  Both verified **fixed on Turso main 0c9fe0dd9** (tursodb built from source): recorded in `latestbugs/`, not filable.
- 1 h hunt on the pip releases: ~890 Turso differences were follow-on noise of T-06 plus T-05; a DuckDB plan-variant
  difference was flaky (GROUP BY on VARIANCE). Decision: hunt only on newest builds (`configs/turso_main.yaml`,
  `scripts/build_turso_main.sh`).
- Tests: 197 passed, 1 skipped.

## 2026-11-08 (wrap-up): every remaining task has code or a script; long runs moved to future work
- Owner's decision: wrap the project up tonight (end-semester exams); no long campaigns, no result-chasing; what is
  left is written down in `docs/generalized/FUTURE_WORK.md`.
- D1/D3: `pgfuzz hunt` (campaign per engine, triage x3 of new failures, package drafts, HUNT.md) and `pgfuzz package`
  (native regression test in DuckDB `.test` / DataFusion and SQLite `.slt` / Turso `.sqltest`, repro.sql, report.md,
  issue.md). Smoke: a 20 s DataFusion round produced 3 reproducible package drafts.
- A3: overlay miner (`sample --execute --mine-overlay`): failing grammar alternatives become `%drop` lines, with a
  guard against blaming parents for their children. DuckDB without its manual overlay: 32.1 % -> 44.1 % statement
  validity after one mined round (`grammar/overlays/duckdb.mined.pgg`, 134 directives).
- C6: `pgfuzz import-tests` (sqllogictest `.test`/`.slt`, Turso `.sqltest` -> seed files). DataFusion suite: 406 seed
  files, 19602 statements, 83 % execute; DuckDB optimizer tests: 134 files.
- D4: `pgfuzz ledger` -> `docs/generalized/LEDGER.md` (precision per engine x oracle, package status, filed links from
  `docs/bughunt/filed.yaml`).
- C5: `scripts/coverage/` (gcov sqlite3 shell from the SQLite source, per-file line coverage, DuckDB lcov script,
  Spearman correlation). Smoke: 200 SQLite test cases cover 69.4 % of the optimizer files' lines.
- E2: `scripts/baselines/` (SQLancer build/run/summary; the build itself was refused by the sandbox: future work).
- E3: `scripts/bench/duckdb_fixes.py` (334 candidate fix commits since May 2026; works on the blob-less clone) and
  `duckdb_reinject.sh` (revert src/, build, keep bugs whose own test fails).
- E4: `scripts/eval/make_configs.py` writes 11 configs (`configs/eval/e4_*`: rules, synthesis, suite seeds per engine;
  normalizers off/on) from the engine configs; `scripts/eval/run_all.sh` (DRY=1 passes; 15 s smoke of 5 arms ran).
- E5: `docs/generalized/paper/OUTLINE.md`.
- Validity measured again (600 test cases): Turso 93.3 % of queries (95.4 % statements); DataFusion 79.4 % of queries
  (86.5 % statements), so B4 stays below its 95 % target (future work).
- Filed by the owner: Turso #11594 / PR #11595 (T-05), DuckDB #28551 / PR #28552 (D-01), DataFusion #27235 /
  PR #27236 (DF-01).
- Tests: 192 passed, 1 skipped.

## 2026-11-08 (night): T-05 second review follow-up
- Two findings on tursodatabase/turso#11595 (head fcfc80b): duplicated percentile step, fraction not validated like
  SQLite. One commit: shared `fraction_step` with the upper bound as a parameter (as SQLite's mxFrac), SQLite's
  fraction errors and order of checks, one first-error slot; core/percentile.rs -25 lines. 8 new sqltest cases checked
  against SQLite 3.54.1 (7 fail without the change); corpus, unit tests, fmt and clippy pass. Push to the fork is
  refused from this environment, so the commit is `followup-fraction.patch` in the T-05 package.
- The `big-db` corpus tests need ~10 GB of temporary files; run them with the disk mostly free.

## 2026-11-08 (later): T-05 review follow-up
- Review finding on tursodatabase/turso#11595: percentile aggregates must reject non-numeric (TEXT/BLOB) input as
  SQLite does. Fixed in core/percentile.rs (one commit on top of the PR head 79d092a), 5 new sqltest cases checked
  against SQLite 3.54.1; full sqlite-sqltests corpus 12707 passed, fmt and clippy clean; JS backend not run locally.
  Pushing to the fork was refused from this environment, so the commit is in
  `docs/bughunt/turso/T-05-percentile-expression-argument/followup-nonnumeric.patch`; the owner updates the PR branch.

## 2026-11-08
- Bug packages (owner's request: turn the 7 verified bugs into ready-to-file issue + PR packages). Each engine's
  development code was built from source: DuckDB `main` d4eea3f208 (`make release`), DataFusion `main` bc86321
  (`datafusion-cli`, sqllogictests, `--profile ci`), Turso `main` 9b71df9ab (`tursodb`, sqltest runner).
  - Still failing on main, fixed here with regression tests in the project's own format: D-01 (DuckDB), DF-01 and
    DF-02 (DataFusion), T-05 (Turso). Each package has `fix.patch` (author Venu Kummari), `issue.md`, `pr.md`
    (project PR template), `steps.md` (fork, `git am`, build/test commands, issue then PR) and an updated
    `report.md` (versions, root cause, test results, duplicate searches via the GitHub REST search API).
  - Already fixed upstream (marked, do not file): D-02 by 57a6875edf (PR #28246; confirmed by reverting only that
    change), T-01 by 44fe44520 (Turso's SQLite-style RIGHT/FULL join rewrite, which removed the error),
    T-02 by merge 8f1f6ee83 (found with `git bisect --first-parent`, building `tursodb` per step). T-01's
    commit was confirmed by building the merge and its parent.
  - DF-01 turned out wider than reported: the WHERE clause of UPDATE and DELETE is affected the same way; the fix
    and tests cover both.
  - Test results: D-01 fast `unittest` suite passes (8751 test cases); DF-01/DF-02 all 546 sqllogictest files and
    clippy pass; T-05 full `sqlite-sqltests` corpus passes (12700). Every new test fails without its fix.
- C3 (first version): Z3 data synthesis for TLP/NoREC predicates (three-valued encoding; CASE, COALESCE, NULLIF,
  LIKE, BETWEEN, IN; join ON conditions satisfied where possible), opt-in `data_synth`; partition-vacuity
  measurement (`metamorphic.measure_partitions`). Measured on DuckDB (300 test cases): among TLP checks whose
  predicate reads a column, 40 % non-vacuous with synthesis vs 34 % without; about half of all vacuous checks have a
  predicate that reads no column (constants, EXISTS), and many partition a SELECT nested in an outer query whose
  own filter decides the rows. Not the "halve vacuity" target yet (next: restrict / weight TLP toward top-level
  cores and column predicates; solve for the outer query too).
- C4 (first version): `pgfuzz learn-normalizers` learns value normalizers and guards from shallow grammar probes.
  DuckDB vs SQLite (3000 probes, depth 6, learned on half, measured on the other half): disagreement 30.8 % ->
  3.3 % after normalizers (`float32`, `bool_int`, `integral_float`) -> 2.5 % after guards (`fn:MIN`, `fn:MAX`,
  `fn:FORMAT`; 1.1 % of comparisons skipped). Rules in `src/normalizers/duckdb__sqlite.yaml`. Turso vs SQLite
  needed none. First cross-engine campaign (`configs/duckdb_vs_sqlite.yaml`, depth 7) was still too noisy
  (dozens of mismatch signatures in minutes; the ones checked were dialect differences: floats/booleans printed
  inside text, integer division, ROUND on NUMERIC). Next for C4: features for values inside text and operator/type
  pairs, then measure campaign precision on a hand-labelled sample (RQ5).
- C5 started: SQLite trunk (GitHub mirror, 8581447, 3.55.0) amalgamation generated (Tcl installed with apt);
  next: build APSW 3.54.1 against it with `--coverage` (the `pip download --no-binary` of APSW's source failed in
  this session; fetch the source from the APSW GitHub repository instead), then gcov per arm.
- Contribution policies of DuckDB, DataFusion and Turso read and recorded under Open decisions.
- Next: C5 coverage builds (SQLite trunk with gcov, DuckDB if disk allows), D1 campaign agent; a DuckDB-vs-SQLite
  cross-engine campaign with the learned rules; triage of new candidates into packages.


## 2026-11-07
- Done: A4 (workers die with their parent, run kills its process group), A1 (`pgfuzz/targets/base.py`: Driver +
  WorkerExecutor; DuckDB, SQLite, Turso drivers), A2 (overlay directives with cascading, element-level removal,
  type classes), dialect transforms (`x::T` to `CAST`), per-dialect literal/fill tables, `sample --execute` validity
  and error examples, generic CrossVersionExecutor (any engine pair).
- Measured validity (`sample --execute`, 600 test cases): DuckDB nightly 96.3 % of queries (from 24 % with the plain
  PostgreSQL grammar); SQLite 3.54.1 97.7 %; Turso 0.8.3 92.7 %.
- Rule switches verified: SQLite's 30 optimizer switches change plans exactly for the expected rule
  (QueryFlattener, SimplifyJoin, MinMaxOpt), first evidence for C1.
- Bugs: DuckDB D-01 packaged (see above). Lead T-01 (Turso): `FULL JOIN ... ON t.a = u.a` rejected with
  "requires an equality condition" when `u.a` is an INTEGER PRIMARY KEY; to check against Turso's docs/limits.
- Campaigns running: DuckDB nightly vs 2.0.0 (2 trials x 2 h), Turso vs SQLite (1 trial x 2 h).
- Decision: keep `postgres.pgg` as the base grammar ("core") and express every engine as overlays on it (the course
  project's grammar stays the single source); engine-specific features live in the overlays' second part.
- Next: triage campaign candidates; C1 rule-firing feedback; B4 DataFusion.

## 2026-11-06
- Done: plan v2 (`PLAN.md`): thesis (rule-directed fuzzing), novelty table against SQLancer++, ShQveL, Sedar,
  Mozi, DQP, QPG, WhiteFox, DBcover, HyLLfuzz, Argus, SQLxDiff, ARG; decisions D1-D12; tasks A1-A4, B1-B5,
  C1-C6, D1-D4, E1-E5, P1-P4; evaluation RQ1-RQ7 sized for 4 cores.
- Checked: pip wheels available (duckdb 2.1.0.dev nightly, datafusion 55, pyturso 0.8.3, chdb 4.4, polars,
  z3-solver); GitHub clones work (sqlite/sqlite mirror, tursodatabase/turso, sqlancer); sqlite.org and
  other download hosts are blocked; GitHub REST API is not available for unattached repos; Java + Maven present.
- PostgreSQL status (verified on master 6 Nov): 6 of the 9 reported bugs fixed (#19803 abda2a2, #19771 776df8a,
  statistics b0392c2, NOT IN b7eee09, #19768 e405a46, IGNORE NULLS 69b20fd); 5 of the fixes are the team's patches.
- Decision (owner, 6 Nov): the LLM extension comes last (Phase L in PLAN.md), after all other work;
  C2 is now rule-targeted generation without an LLM; C6 uses engine test suites as seeds.
- Next: A4, A1, A2, then B1 (DuckDB to 95 %) and start the DuckDB campaign.


One dated entry per work session: done, measured numbers, next, questions for the owner.

## 2026-11-02 (previous session, before hand-off)
- Done: plan (PLAN.md), hand-off notes (HANDOFF.md), DuckDB executor (crash-isolated worker,
  transactions, optimizer-off plan variants, metamorphic checks), DuckDB schema and config.
- Measured: DuckDB nightly 2.1.0.dev runs the PostgreSQL grammar unchanged with poor validity
  (300 test cases / 992 statements; top errors: jsonb `?` operator 336, unnamed CREATE INDEX,
  SET LOCAL, EXPLAIN options, int4range, jsonb_* functions).
- Next: dialect overlay mechanism (G2) and DuckDB overlay to ≥95 % validity, then campaigns.
- Open: `cargo build` for DataFusion main was blocked in that session (see Blocked).
