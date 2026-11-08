# Plan v2: Arbor, an autonomous, rule-directed fuzzer for SQL engines (A* paper, deadline ~Jan 2027)

Branch `generalized` of https://github.com/v28k/cs5187-term-project. Rules: `CLAUDE.md` and
`docs/generalized/HANDOFF.md` section 1 (commit identity `v28k <v.kummari@iitg.ac.in>`; bug filing is the
owner's). Keep the **Status** column current and log every session in `docs/generalized/PROGRESS.md`.
Plan v2 (6 Nov 2026) replaces plan v1; section 9 maps the old task IDs G1–G11 onto the new ones.

**Owner decision (6 Nov 2026): the LLM extension comes last.** Phases A–E are done without any LLM; the LLM
tasks are collected in Phase L (section 4) and are started only after *all* other work is finished, if time allows.
The paper's contributions must therefore stand without an LLM.

---

## 1. Thesis and what is new

The course project showed that a typed grammar with derivation trees, oracles on those trees and an
LLM that reads recent commits find real bugs in PostgreSQL: 9 reported, 6 fixed upstream, 5 of the fixes ours.
Plan v2 **generalizes that project** to many SQL engines and adds four techniques. Each technique comes from
a mechanism the course project already has:

| Course-project mechanism (exists) | Generalized technique (new) |
|---|---|
| plan-variant oracle with PostgreSQL `enable_*` switches | **rule-firing feedback**: per-engine optimizer-rule toggles say *which rule a query exercises*; this gives an engine-agnostic "rule coverage" signal and steers generation |
| bandit-weighted grammar alternatives | **rule-targeted generation**: learn which grammar alternatives make which rules fire and, when rule coverage stalls, steer generation toward unfired and rare rules (an LLM solver for still-unfired rules is the optional Phase L) |
| TLP / NoREC checks on random data | **constraint-based data synthesis**: predicates from the typed tree go to Z3, which yields rows that make every oracle partition non-empty (no *vacuous* checks) |
| cross-version differential, soundness fixes written by hand | **learned semantic normalizers**: cross-engine differential testing whose dialect differences are *inferred by probing* and stored as data |
| triage: reduce, localize, report draft | **autonomous campaign agent**: schedule → find → reduce → localize to a rule → validate on nightly → dedup → native regression test → filing package |

**One-sentence thesis (working):** optimizer rules are the natural unit for testing SQL engines; Arbor
observes rule firing in unmodified engines, steers a typed grammar toward unfired rules (learned
alternative→rule statistics) and an SMT data solver, and checks each rule with oracles whose cross-engine soundness rules are
learned, not hand-written.

**Working title (owner decides):** "Arbor: Rule-Directed Fuzzing of SQL Engines" (placeholder).
**Venue:** TBD by the owner (ISSTA / FSE / ICSE / OOPSLA / CCS / USENIX Security; deadline ~Jan 2027).

### 1.1 Novelty check against the closest work (keep this table in the paper's related work)

| Closest work | What it does | How Arbor differs |
|---|---|---|
| SQLancer++ (Zhong & Rigger, arXiv 2503.21424) | one adaptive generator for 18 DBMSs; learns which features an engine accepts | we keep a typed grammar and *mine* verified dialect overlays; our feedback is rule firing, not validity; we add rule-targeted generation, data solving and learned cross-engine normalizers |
| ShQveL (Zhong & Rigger, arXiv 2505.02012) | LLM fills SQL sketches with feature fragments, validated by execution | Arbor's core uses no LLM; the optional Phase L solver differs: called only at a roadblock, for a specific unfired rule, reads the rule's source, accepted only if the rule fires |
| Sedar (ICSE'24), QTRAN | transfer seeds / tests across DBMSs | we transfer generators, not tests; test suites are only context for the solver |
| Mozi (ICSE'24), DQP (SIGMOD'24) | configuration / hint toggles as an oracle | we reuse toggles as an oracle, but our contribution is toggles as **feedback and coverage** (rule coverage, rule-pair coverage), plus rule-level localization |
| QPG (ICSE'23) | plan-shape novelty as guidance | plan shapes stay a secondary signal; rule firing is finer and gives localization |
| WhiteFox (OOPSLA'24), DBcover (arXiv 2608.25573) | LLM reads optimizer source (compilers) / LLM with line coverage (PostgreSQL, MySQL) | no instrumented build and no LLM needed; the target is a rule-firing predicate observable on release binaries; steering changes a reusable grammar's weights, not single tests |
| HyLLfuzz (arXiv 2412.15931) | LLM as concolic solver at coverage roadblocks (C programs) | same "act at a roadblock" idea, transplanted to SQL engines with rule firing as the branch condition; our core does it by statistics, Phase L by an LLM |
| Argus (arXiv 2510.06663), EET (OSDI'24) | LLM-proposed / hand-made equivalent-query oracles | orthogonal: we keep our tree rewrites and make them non-vacuous via data solving |
| SQLxDiff (ISSTA'25) | cross-DBMS differential with manual clause mappings | our normalizers are inferred automatically by probing, with measured precision |
| ARG (ASE'25) | abstract-rule-guided fuzzing of query *rewriters* (Calcite, WeTune) | production engines, black-box firing signal, rule-targeted generation, bug campaigns |
| PQS, TQS, Radar, data-centric work | pivot rows / schema graphs / data reduction | SMT synthesis of rows from the typed predicate tree to make *every* TLP partition non-empty |

Rule: before the paper is written, re-run this search (ICSE'26/27, ISSTA'26, FSE'26, SIGMOD'26, VLDB'26,
arXiv) and add any new close work to this table (task P3).

## 2. Decisions (taken; change only with a recorded reason in PROGRESS.md)

| # | Decision | Choice | Why |
|---|---|---|---|
| D1 | Tier-1 targets | **DuckDB** (nightly wheel), **SQLite** (trunk from the GitHub mirror, built here), **Turso** (pyturso, SQLite-compatible Rust rewrite), **DataFusion** (pip 55, then `main`) | all run in-process on this machine (4 cores, 15 GB RAM); active development = many fresh bugs; all have GitHub trackers the owner can file on; Turso↔SQLite is a near-perfect differential pair |
| D2 | Tier-2 targets (after tier 1 is productive) | **ClickHouse via chDB** (pip), **Polars SQL** (pip) | in-process, no server; big bug surfaces. MySQL/MariaDB/CockroachDB/TiDB need downloads from hosts this network blocks; revisit only if the owner provides a machine |
| D3 | PostgreSQL | evaluation-only target (existing results, cross-version oracle); **no new hunting** | owner's rule |
| D4 | Main feedback signal | **rule firing** (+ plan shapes), engine-agnostic, works on release builds | no instrumentation; tied to the optimizer, where most logic bugs live; gives localization for free |
| D5 | Code coverage | only as **ground truth and extra feedback** on SQLite (clang `-fsanitize-coverage` / gcov build) and DuckDB if a debug build fits disk and time | validates "rule coverage" as a proxy (an RQ) without making the tool depend on instrumentation |
| D6 | LLM use | **none in Phases A–E** (owner's decision); all LLM work is Phase L, done last if time allows (roadblock solver, overlay patches, normalizer labels, triage summaries; never per query) | contributions must stand without an LLM; model/key is the owner's decision when Phase L starts |
| D7 | Data solver | **Z3** (`z3-solver` pip) on the typed predicate subset; unsupported functions are treated as unconstrained | typed trees make the translation direct |
| D8 | Language / isolation | stay in Python; each engine runs in a **spawned worker process** (crash = dead worker); SQLite through a small **ctypes** binding (needed for `sqlite3_test_control(SQLITE_TESTCTRL_OPTIMIZATIONS)` and EXPLAIN QUERY PLAN) | reuse 10.5k lines; one isolation model for all engines |
| D9 | Oracles per engine | crash / internal error / hang; TLP, NoREC, expression rewrites (existing); rule ablation (one rule off); cross-version (nightly vs last release); cross-engine (with learned normalizers); Turso vs SQLite trunk | strongest precise oracles first; cross-engine only with measured precision |
| D10 | Repository | keep working in `v28k/cs5187-term-project`, branch `generalized` (the hand-off's "new repo for the friend" is void) | owner's repo, history preserved |
| D11 | Compute | 4 cores: at most **3 fuzz workers** + 1 for triage/build; long campaigns run in the background with a watchdog; evaluation budgets sized for this machine (section 6) and scaled up if the owner provides machines | honest, reproducible numbers |
| D12 | Paper tool name | **Arbor** (`\tool`, as in the course paper); code package stays `pgfuzz` (rename to `arbor` in P1 if cheap) | continuity |

## 3. Architecture (target state)

```
                 engine repo @ tested commit (rule sources, test suites, recent commits)
                                   │ context
  core.pgg + dialect overlays ──► typed grammar ◄──── rule targeting (alternative→rule stats) ── observed firing
  (mined + hand-written)             │                                                   │
                                     ▼                                                   │
        derivation trees ──► oracle attachers ──► Target adapter (worker process) ───────┘
        (+ corpus, seeds)    TLP/NoREC/rewrites    execute, error taxonomy, rules + toggles,
              ▲              rule ablation          EXPLAIN → plan + fired rules, versions, reset
              │              x-version, x-engine         │
              │              crash/internal/hang         ▼
              │       Z3 data synthesis ──► non-vacuous checks
              │                                          │
  feedback: rule coverage, rule pairs, plan shapes, (code coverage on SQLite), bandit over
            (engine × oracle × grammar region)
                                                          │ failures
  autonomous triage: reproduce ×3 on newest build → tree+token reduce → localize to rule/setting →
  dedup (signature, upstream commits/tests/issues) → native test (.test/.slt) → filing package → PROGRESS.md
```

## 4. Tasks

Effort: S ≤ ½ day, M ≈ 1–2 days, L ≈ 3–5 days of focused work. Order = priority. **Bug campaigns start as
soon as an engine reaches ≥95 % validity** and keep running in the background while later tasks are built.

### Phase A: foundation (portable core)

| ID | Task | Acceptance criteria | Effort | Status |
|---|---|---|---|---|
| A1 | **Target abstraction**: `Target` interface (`execute`, `explain` → normalized plan, `rules()` + `with_rules_off(set)`, error→outcome taxonomy, `version()`, `reset()`, capabilities flags) + YAML spec; port PostgreSQL and DuckDB to it, no behaviour change on PostgreSQL | `pytest` green; PostgreSQL rediscovery config still finds all 9 bugs; adding an engine = adapter + overlay + schema | M | done (PG unchanged; DuckDB/SQLite/Turso drivers) |
| A2 | **Dialect overlays** in the DSL: `%drop <rule> "<alt substring>"`, `%droptype <T>`, `%replace`, `%include core.pgg`; split `postgres.pgg` into portable `core.pgg` + `postgres.pgg` | unit tests per directive; PostgreSQL validity unchanged | M | done |
| A3 | **Overlay miner**: run every grammar alternative in isolation (k samples) against an engine, cluster errors, auto-write a draft overlay (drops + type renames + known rewrites from a small rule table), gate re-measures (LLM patches: Phase L) | a first DuckDB overlay produced automatically; report "manual lines vs mined lines" per engine (RQ1 data) | M | todo |
| A4 | **Harness hardening**: process groups (stopping a run kills all workers), per-worker memory limit, timeouts per engine, no orphans, crash/hang isolation for in-process engines | kill test: no process left after `Ctrl-C`/`kill`; a deliberate engine abort becomes a CRASH candidate | S | done |

### Phase B: targets (validity first, then campaigns)

| ID | Task | Acceptance criteria | Effort | Status |
|---|---|---|---|---|
| B1 | **DuckDB**: overlay to ≥95 % valid; DuckDB features (LIST/STRUCT/MAP, lambdas, QUALIFY, ASOF/POSITIONAL JOIN, PIVOT/UNPIVOT, GROUP BY ALL, window EXCLUDE/FILTER, DISTINCT ON, arg_max, UNNEST…); rules = `duckdb_optimizers()`; cross-version = last release vs nightly (two venvs, two workers) | `sample --execute` 300 cases ≥95 %; 4×1 h run clean; unit tests | M | done; campaign running |
| B2 | **SQLite**: build trunk (GitHub mirror) as `libsqlite3.so` (+ a gcov/SanCov variant for D5); ctypes adapter; rules = `SQLITE_TESTCTRL_OPTIMIZATIONS` bits; EXPLAIN QUERY PLAN parser; overlay | ≥95 % valid; rule toggles verified on a known query; 4×1 h run clean | M | done (APSW 3.54.1; trunk build blocked) |
| B3 | **Turso** (pyturso; later a build from `main`): shares the SQLite overlay minus unsupported features (mined by A3); **Turso↔SQLite differential oracle** | ≥95 % valid on Turso's supported subset; differential precision measured on 1 h | S | done; campaign running |
| B4 | **DataFusion** (pip 55, then `main` via maturin if the build is allowed): adapter, overlay, rules from `datafusion.optimizer.*` + `EXPLAIN VERBOSE` (per-rule plans give firing directly) | ≥95 % valid; 4×1 h run clean | M | in progress (adapter + campaign on pip 55; `main` builds from source since 8 Nov) |
| B5 | Tier 2: **chDB (ClickHouse)**, **Polars SQL** | each ≥90 % valid, one campaign | M | todo |

### Phase C: the new techniques (the paper's contributions)

| ID | Task | Acceptance criteria | Effort | Status |
|---|---|---|---|---|
| C1 | **Rule-firing observability**: `fired(q) = {r : plan(q) ≠ plan(q, r off)}` (or the per-rule trace where the engine has one: DataFusion `EXPLAIN VERBOSE`, DuckDB per-optimizer profiling if available); sampling + caching by plan shape to bound cost; metrics *rule coverage* and *rule-pair coverage*; corpus keeps test cases with new rules/pairs; **rule-ablation oracle** with rule-level localization | overhead ≤25 % of throughput at default sampling; rule coverage curves per engine; unit tests | L | first version (rule-firing probe as feedback and coverage, c676a4d; overhead and curves not yet measured) |
| C2 | **Rule-targeted generation** (no LLM): keep statistics P(rule fires \| grammar alternative, operator context) from C1 observations; on a stall (no new rule/pair for T min) pick a target among unfired/rare rules and reweight alternatives toward it (bandit over targets, Thompson sampling); mutate corpus test cases that are *near misses* (plan has the operators the rule matches); seed from engine tests that fire the rule (C6) | rule and rule-pair coverage higher than C1-only feedback (A12 > 0.7) on DuckDB and SQLite | M | first version (rule-targeted boosting after stalls; not evaluated) |
| C3 | **Constraint-based data synthesis**: translate the predicate subtree (comparisons, AND/OR/NOT, IS NULL, BETWEEN, IN lists, LIKE prefix, arithmetic on ints/decimals/strings with 3-valued NULL) to Z3; solve for rows making each TLP partition (and NoREC sides) non-empty, plus boundary/NULL/duplicate rows; insert into per-test scratch tables; measure **vacuity rate** (checks whose compared results are empty/trivial) | vacuity rate at least halved on DuckDB and SQLite; no validity loss; unit tests | L | first version (Z3 synthesis + partition-vacuity metric; gain small so far: 34 % -> 40 % non-vacuous on column predicates) |
| C4 | **Learned semantic normalizers + cross-engine oracle**: probe generator (per operator/function/type, small typed probes) → run on engine pairs → cluster disagreements → infer rules (output normalizers such as float rounding, NULL ordering, boolean/integer rendering; query guards such as "skip `/` on ints for SQLite↔DuckDB") matched against a library of normalizer templates, stored as YAML; validate on held-out probes; cross-engine oracle uses the rules | precision of cross-engine oracle before/after normalizers on 1 h per pair; ledger per pair | L | first version (`learn-normalizers`; DuckDB vs SQLite held-out disagreement 28.7 % -> 3.6 %) |
| C5 | **Code-coverage ground truth** (SQLite; DuckDB if feasible): coverage of the optimizer files per arm; correlation of rule coverage with line/branch coverage of rule code | Spearman ρ per engine reported; coverage plots | M | todo |
| C6 | **Engine test suites as seeds** (no LLM): parse DuckDB `test/sql/**/*.test`, SQLite `test/*.test`, DataFusion `*.slt`; keep statements our grammar parses into derivation trees as corpus seeds; index them by the rules they fire (C1) for C2 | ≥30 % of suite queries tree-ified per engine; seeds raise rule coverage at t=10 min | M | todo |

### Phase D: autonomy (find → package without a human)

| ID | Task | Acceptance criteria | Effort | Status |
|---|---|---|---|---|
| D1 | **Campaign agent** `arbor hunt --targets … --budget …`: bandit over (engine × oracle × grammar region) by yield × precision; daily nightly upgrade (DuckDB wheel, SQLite/Turso git pull + rebuild); watchdog; disk guard | 24 h unattended run on 3 engines with no harness error | M | todo |
| D2 | **Autonomous triage**: reproduce ×3 on the newest build, tree+token reduction, localization to rule/setting/version, cross-engine signature dedup, known-bug catalog per engine, upstream dedup against cloned repo history (commits, test files) and issue text where reachable | ≥90 % of candidates reduced to ≤15 lines automatically | M | todo |
| D3 | **Native test emission + filing package generator**: sqllogictest (`.test` for DuckDB/SQLite, `.slt` for DataFusion, Turso's format), `report.md`, `issue.md` (engine's issue template), `repro.sql`, `steps.md`; root-cause pointer from rule localization (rule → source file) | package passes the HANDOFF 1d checklist without manual edits for ≥70 % of real bugs | M | todo |
| D4 | **Precision ledger per engine × oracle**, dashboards (`runs/*/summary.md`) | regenerated by one script | S | todo |

### Phase E: evidence and paper

| ID | Task | Acceptance criteria | Effort | Status |
|---|---|---|---|---|
| E1 | **Bug campaigns** (continuous from B1 on): DuckDB, SQLite, Turso, DataFusion, then tier 2; validate; filing packages in `docs/bughunt/<target>/` | target ≥20 confirmed bugs over ≥4 engines, ≥half logic bugs | ongoing | ongoing (7 packages re-checked on main 8 Nov: 4 ready with fixes, 3 fixed upstream) |
| E2 | **Baselines**: SQLancer (Java/Maven available; DuckDB, SQLite, DataFusion, PostgreSQL), SQLancer++ / ShQveL if their artifacts run, SQLsmith where it runs | each baseline runs under our budget with a script | M | todo |
| E3 | **Re-injected bug benchmark** for DuckDB (and SQLite if cheap): revert recent fixes that have regression tests; one build per bug or a fault-flag build | ≥15 verified bugs; attribution script | L | todo |
| E4 | **Evaluation runs + statistics** (section 6): configs `configs/eval/*.yaml`, scripts `scripts/eval/*` that regenerate every table/plot; Mann–Whitney U, Vargha–Delaney A12, bootstrap CIs | dry runs pass; all numbers from scripts | M | todo |
| E5 | **Paper** (acmart): framing of section 1, related work (table 1.1 + grammar fuzzers, Squirrel, SQLRight, Griffin, Fuzz4All, WhiteFox…), approach, evaluation, threats, artifact; placeholders for venue/authorship/AI statement | draft mid-December; full version early January; builds within the venue's page limit | L | todo |

### Phase L: LLM extension (only after all of A–E and P are done, if time allows)

| ID | Task | Acceptance criteria | Effort | Status |
|---|---|---|---|---|
| L1 | **LLM rule solver** at roadblocks: for rules C2 cannot reach, the LLM reads the rule's source at the tested commit (+ tests, grammar excerpt, schema, near-miss query and plan) and writes grammar productions; gate = parses, ≥60 % valid, **fires the rule**; ≤3 repair rounds; ledger (tokens, cost, accept rate) | ≥50 % of C2-unreachable rules solved on DuckDB; ablation vs C2 | L | deferred |
| L2 | LLM patches for overlay-miner error clusters (A3) | fewer manual overlay lines | S | deferred |
| L3 | LLM labels for normalizer clusters no template matches (C4) | more engine pairs with precise oracles | S | deferred |
| L4 | LLM root-cause summaries in filing packages (D3), marked unverified until checked | — | S | deferred |
| L5 | recent-commit context (the course project's LLM arm, generalized) | — | M | deferred |

### Phase P: project hygiene (small, any time)

| ID | Task | Status |
|---|---|---|
| P1 | rename package `pgfuzz` → `arbor` (keep a `pgfuzz` alias) if it costs < ½ day | todo |
| P2 | README for the generalized tool: install, add-an-engine guide, one-command hunt | todo |
| P3 | re-run the related-work search before writing (section 1.1) | todo |
| P4 | free disk: remove PostgreSQL build trees not needed for evaluation (keep `install/base` and `REL_18_STABLE`) | todo |

## 5. Order of work (fast path to bugs, then contributions)

1. A4 → A1 → A2 (one stretch; foundation).
2. B1 (DuckDB ≥95 %) → **start the DuckDB campaign in the background** (E1).
3. B2 + B3 (SQLite + Turso; share one overlay) → start Turso↔SQLite differential campaign.
4. C1 (rule firing; uses the toggles already in every adapter) → switch campaigns to rule feedback.
5. B4 (DataFusion) → campaign.
6. C3 (data synthesis) → C6 + C2 (test-suite seeds, rule-targeted generation) → C4 (normalizers + cross-engine).
7. D1–D4 (autonomy), triage packages continuously as candidates arrive.
8. A3 (overlay miner; needs several engines to be meaningful), C5 (coverage ground truth), B5 (tier 2).
9. E2 → E3 → E4 → E5. Draft paper mid-December.
10. Phase L (LLM extension) only if everything above is done.

## 6. Evaluation design (sized for 4 cores; scale up if more machines appear)

| RQ | Question | Setup | Metrics |
|---|---|---|---|
| RQ1 Portability | How much per-engine effort, and does the core transfer? | 4 tier-1 engines (+ tier 2, + PostgreSQL) | validity, adapter/overlay LOC, mined vs manual overlay lines, oracles applicable unchanged |
| RQ2 Bugs | Does Arbor find new bugs across engines? | campaigns (E1) | confirmed / fixed bugs by engine, kind (crash, logic, internal error, hang), oracle, technique |
| RQ3 Rule feedback + targeting | Does rule direction help? | arms: base / +rule feedback (C1) / +rule targeting (C2) / +seeds (C6); 5 trials × 2 h per engine (3 engines) = 120 core-hours | rule coverage, rule-pair coverage, code coverage (SQLite), plan shapes, bugs (benchmark) |
| RQ4 Data synthesis | Does solving data make oracles non-vacuous? | with/without C3, same trials | vacuity rate, bug detection on the re-injected benchmark, time to bug |
| RQ5 Cross-engine soundness | Do learned normalizers make cross-engine testing precise? | engine pairs, 1 h each, hand-labelled sample | precision before/after, bugs found only by this oracle |
| RQ6 State of the art | Arbor vs SQLancer (and SQLancer++/ShQveL if runnable) | same budget, same engines | bugs on the benchmark, coverage, unique bugs |
| RQ7 Cost / autonomy | What does it cost, how much human time remains? | ledgers | rule-observation overhead, packages needing no manual edit, minutes of human time per filed bug |

Statistics: medians, Mann–Whitney U, Vargha–Delaney A12, bootstrap 95 % CIs; every table and plot from
`scripts/eval/`.

## 7. Paper claims (each backed by one RQ)

1. One typed grammar core with mined overlays reaches ≥95 % validity on every tier-1 engine (RQ1).
2. New, confirmed bugs on ≥4 engines, many of them logic bugs (RQ2).
3. Rule-firing feedback plus rule-targeted generation increase rule and code coverage and bug finding over
   grammar generation alone (RQ3), at a measured cost (RQ7).
4. Data synthesis removes most vacuous checks and finds benchmark bugs the plain oracles miss (RQ4).
5. Learned normalizers turn cross-engine differential testing from noisy into precise (RQ5).
6. Arbor beats SQLancer-family tools under the same budget on shared engines (RQ6).

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| no time / key for the LLM | nothing in A–E depends on an LLM; Phase L is optional |
| 13 GB free disk | P4 cleanup; build one engine at a time; keep only the newest builds |
| 4 cores | ≤3 workers; evaluation sized in section 6; more machines = owner decision |
| `cargo build` blocked by permissions | use pip wheels (DataFusion 55, pyturso) first; record in PROGRESS.md "Blocked" |
| sqlite.org not reachable | GitHub mirror `sqlite/sqlite` (verified reachable) |
| GitHub API not available for duplicate search | search cloned repos (commits, tests, changelogs); the owner does the final issue search before filing (steps.md says so) |
| rule toggles missing on an engine | fall back to plan-shape feedback and code coverage; report it |
| close new related work appears | P3 search before writing; adjust claims, not facts |

## 9. Mapping from plan v1

G1→A1, G2→A2+A3, G3→B1, G4→B4, G5→C4 (+B3), G6→C6 (LLM part → L5), G7→A4+D1–D4, G8→E4, G9→E1, G10→E3, G11→E5.
