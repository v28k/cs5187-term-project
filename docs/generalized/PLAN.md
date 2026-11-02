# Plan: a high-level, target-independent SQL engine fuzzer and an A* paper (deadline ~January 2027)

Branch `generalized`. Rules for working on it: `docs/generalized/HANDOFF.md` section 1.
Keep the **Status** column below current and log every session in `docs/generalized/PROGRESS.md`.

## 1. Goal and paper claims

Build on everything the PostgreSQL project produced (typed grammar and derivation trees,
tree-based metamorphic oracles, plan-variant / cross-version / CERT / hang oracles, tree +
token reduction, localization, the precision ledger, the engine-gated LLM extension, the
re-injected bug benchmark) and turn it into **one fuzzer for many SQL engines**, then show
that the approach finds new bugs across engines with measured oracle precision.

Target venue: a top software-engineering / testing / security venue with a deadline around
January 2027 (ISSTA usually has a late-January deadline; also check ICSE, FSE, ASE, OOPSLA,
CCS/USENIX Security CFPs and pick with the owner). Format: ACM `acmart` (the course paper in
`paper/` is a starting point but needs a new framing and new evaluation).

Claims the paper must support (each needs an experiment):
1. **Portability.** One typed grammar core plus a small dialect overlay per engine gives
   ≥95 % valid statements on each engine; the tree-based oracles apply unchanged.
2. **Effectiveness.** New, confirmed bugs on several engines (target: ≥15 confirmed,
   several fixed, across ≥3 engines), including wrong results that crash-only fuzzers miss.
3. **Better than the state of the art** in the same budget on shared engines: more bugs and/or
   more coverage and plan diversity than SQLancer (and SQLsmith, Squirrel/SQLRight where they run).
4. **Measured precision.** Per-engine, per-oracle precision ledgers; the false-positive classes
   and the soundness rules that remove them generalize across engines.
5. **Knowledge transfer.** An LLM turns each engine's own regression tests / docs / recent
   commits into grammar fragments; an engine-side gate accepts only valid, reaching fragments;
   ablation shows what this adds (features, coverage, bugs) and what it costs.
6. **Ground truth.** A re-injected-bug benchmark for at least one more engine (e.g. DuckDB
   fixes) shows detection rates and time to bug per oracle family.

## 2. Architecture target ("high-level fuzzer")

```
  dialect overlays ──► typed grammar core ──► derivation trees ──► oracle attachers (TLP, NoREC,
  (per engine)          (+ LLM fragments)       (+ seeds, corpus)    rewrites, plan variants, x-version,
                                                                      x-engine, CERT, hang)
                                     │
                  Target adapter: executor (crash-isolated), error taxonomy, knobs/variants,
                  version pairs, EXPLAIN parser, coverage hook, reset/state, timeouts
                                     │
     triage: reproduce, tree+token reduction, localization, dedup across engines, filing package
                                     │
     feedback: plan shapes, coverage (where cheap), bandit weights, corpus; dashboards and ledgers
```

## 3. Tasks

| ID | Task | Acceptance criteria | Status |
|---|---|---|---|
| G1 | **Target abstraction**: a `Target` spec (YAML + small Python adapter) = executor, dialect overlay(s), schema, error→outcome taxonomy, plan-variant knobs, version pair for cross-version, EXPLAIN shape extractor, reset strategy. Port PostgreSQL to it without behaviour change. | `pytest` green; PostgreSQL configs give the same validity as before; adding an engine = new adapter + overlay + schema only. | todo |
| G2 | **Dialect overlays** in the grammar DSL: `%drop <rule> "<text>"`, `%droptype <T>`, `%rename`, plus added rules; portable `core.pgg` + `postgres.pgg` / `duckdb.pgg` / `datafusion.pgg` / `sqlite.pgg` overlays. | each engine ≥95 % valid in `sample --execute` (300 test cases); unit tests for the directives. | todo |
| G3 | **DuckDB target** (nightly): executor exists (`pgfuzz/targets/duckdb_executor.py`); finish overlay, DuckDB-specific features (lists, structs, maps, lambdas, QUALIFY, ASOF/POSITIONAL joins, PIVOT, GROUP BY ALL, window EXCLUDE…), plan variants from `duckdb_optimizers()`, cross-version (last release vs nightly in two workers), unit tests. | first campaign 4×1 h runs clean (no harness errors); candidates triaged. | in progress |
| G4 | **DataFusion target** (`main`): needs `cargo build` permission (ask owner) or start with pip `datafusion`; executor via Python bindings in a worker process (panics = crash), optimizer-rule toggles as variants, overlay. | ≥95 % valid; campaign; candidates triaged. | todo |
| G5 | **SQLite target** + **cross-engine differential oracle** on the portable subset with normalisation (NULL ordering, integer division, float formatting, type affinity, collations); disagreements go through triage; measure its precision honestly. | ledger per pair of engines. | todo |
| G6 | **LLM knowledge transfer from test suites**: parse each engine's regression tests (DuckDB `test/sql/*.test`, DataFusion `*.slt`, SQLite `test/*.test`, PostgreSQL `regress/sql`) and recent commits; the LLM proposes grammar fragments + rewrites; the existing gate (parse, use, validity, coverage/plan-shape gain) validates on the target; ledger. Model: whatever the owner has (Claude or Gemini via the client's API/manual modes). | ablation numbers per engine. | todo |
| G7 | **Harness hardening**: process groups so stopping a run kills all workers; per-target crash/hang isolation; cross-engine signature de-duplication; automatic triage → filing-package draft (section 1d of HANDOFF). | no orphaned workers; triage produces `report.md`/`issue.md` drafts. | todo |
| G8 | **Evaluation design**: RQs, ≥10 trials × fixed budget (e.g. 12 h or 24 h for bug-finding, 1 h for reach), baselines (SQLancer on PostgreSQL/DuckDB/SQLite/DataFusion; SQLsmith where it runs), statistics (Mann–Whitney U, Vargha–Delaney A12, bootstrap CIs), coverage builds where affordable (DuckDB/SQLite with gcov), scripts that regenerate every table and plot. | `configs/eval/*.yaml`, `scripts/eval/*`, dry runs pass. | todo |
| G9 | **Bug campaigns** on DuckDB nightly, DataFusion main, SQLite trunk (+ others if time: MySQL/MariaDB, CockroachDB, TiDB, Turso/libSQL): triage, validate, **filing packages only** (owner files). | `docs/bughunt/<target>/…` packages; bug table kept current. | todo |
| G10 | **Re-injected bug benchmark for DuckDB** (revert recent DuckDB fixes that have regression tests, as for PostgreSQL RQ3). | verified benchmark + attribution script. | todo |
| G11 | **Paper**: new title and framing, related work (SQLancer TLP/NoREC/PQS/CERT/DQP, SQLRight, Squirrel, Griffin, Sedar, Radar, DQE, EET, SQLsmith, Fuzz4All, WhiteFox/LLM fuzzers, grammar fuzzers), approach, evaluation, threats, artifact (anonymised mirror), AI-use statement (owner decides). Draft by mid-December, full version early January. | paper builds, page limit of the chosen venue. | todo |

## 4. Improvisation ideas (do them when they help; record decisions in PROGRESS.md)

- **Adaptive oracle scheduling**: bandit over oracle kinds by observed precision × yield per engine.
- **Feature-coverage feedback without a coverage build**: plan shapes + SQL feature pairs + error-message
  novelty as corpus criteria (works on any engine).
- **Differential across releases** of the same engine (nightly vs last release) is cheap and precise;
  use it on every engine with pip/binary releases.
- **Query-plan guidance** (QPG-style) using each engine's EXPLAIN (DuckDB `EXPLAIN (FORMAT json)`,
  DataFusion `EXPLAIN`).
- **Auto-reduction to the engine's native test format** (sqllogictest / .slt) so filing packages include a
  ready test.
- **Soundness rules as data**: per-engine semantic quirks (e.g. DuckDB integer division, NULL ordering,
  float output) as declarative normalisers instead of code.
- **Crash/sanitizer builds** where allowed (DuckDB debug build with assertions catches far more than the
  release wheel; ask the owner before building external code).

## 5. Timeline (adjust with the owner)

| When | Milestone |
|---|---|
| Nov, week 1–2 | G1, G2, G3 (DuckDB ≥95 % valid, first campaigns), G7 basics |
| Nov, week 3–4 | G4 DataFusion, G5 SQLite + cross-engine oracle, G9 campaigns running continuously |
| Dec, week 1–2 | G6 LLM transfer, G10 DuckDB benchmark, G8 evaluation scripts; start long runs |
| Dec, week 3–4 | full evaluation runs, triage, filing packages; paper draft (G11) |
| Jan 2027 | final experiments, paper polish, artifact; submit |

## 6. Rules recap

Owner files all bugs and PRs; you prepare packages. Public repo on your GitHub, push after every
finished part, owner's commit identity, no Claude/AI mentions, tests green, PROGRESS.md updated.
Full details: `docs/generalized/HANDOFF.md`.
