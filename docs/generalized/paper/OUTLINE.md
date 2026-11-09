# Arbor: rule-directed grammar fuzzing across SQL engines (paper skeleton, task E5)

Status: skeleton. Numbers that exist are from first versions and smoke runs (8 Nov 2026) and are
marked as such; every `[TBD]` comes from `scripts/eval/run_all.sh` (E4) once the campaigns run.
Venue, authorship and the AI-use statement are the owner's decisions (PROGRESS.md, "Open decisions").

## Abstract (about 200 words)

SQL engines share most of their query language but no fuzzer serves them all well: generic
generators produce many invalid queries, and per-engine fuzzers are expensive to write. Arbor
keeps one typed grammar with derivation trees and adapts it to an engine with small dialect
overlays, partly mined automatically. Instead of code coverage it uses a signal every engine
exposes on release builds: which optimizer rules fire on a query, observed by toggling rules or
reading per-rule plan traces. Rule firing guides generation toward unfired rules, localizes
failures to a rule, and serves as a coverage metric. Z3 synthesizes rows that make metamorphic
checks non-vacuous, and learned value normalizers make cross-engine comparison precise. On
DuckDB, SQLite, Turso and DataFusion, Arbor found [TBD: final count] new bugs; [N] are fixed
upstream. [TBD: RQ3 to RQ6 headline numbers.]

## 1. Introduction

- Problem: logic bugs in optimizers; per-engine fuzzers do not transfer; code coverage needs
  instrumented builds and is a weak proxy for optimizer behaviour.
- Idea: optimizer-rule firing as an engine-agnostic feedback, coverage and localization signal.
- Contributions (each tied to an RQ, PLAN.md section 7):
  1. portable typed-grammar core with mined overlays (RQ1);
  2. rule-firing feedback and rule-targeted generation (RQ3);
  3. constraint-based data synthesis for non-vacuous oracles (RQ4);
  4. learned semantic normalizers for cross-engine differential testing (RQ5);
  5. an autonomous pipeline from campaign to filing package (RQ7);
  6. new bugs in four engines (RQ2).

## 2. Background and motivating example

- Derivation trees and typed grammars (from the course project).
- Example: DataFusion DF-01 (UPDATE with a repeated expression; the common-subexpression rule
  leaks `__common_expr_1` into DML planning). Rule localization names the rule.

## 3. Approach

| Section | Component | Code |
|---|---|---|
| 3.1 | engine abstraction (driver + spawned worker) | `pgfuzz/targets/base.py` and the four drivers |
| 3.2 | dialect overlays and the overlay miner | `pgfuzz/grammar/overlay.py`, `miner.py` |
| 3.3 | rule firing: probe, metrics, rule-ablation oracle | `targets/*.fired`, generator `_rule_feedback` |
| 3.4 | rule-targeted generation (stall detection, Thompson sampling over targets) | generator `rule_target` |
| 3.5 | data synthesis with Z3 | `pgfuzz/datasynth/` |
| 3.6 | learned normalizers and guards | `pgfuzz/normalizers/infer.py`, `eval/normalize.py` |
| 3.7 | seeds from engine test suites | `pgfuzz/agent/suites.py` |
| 3.8 | autonomous loop: hunt, triage, native regression tests, packages, ledger | `pgfuzz/agent/`, `triage/ledger.py` |

## 4. Evaluation

| RQ | Data source | Existing first numbers |
|---|---|---|
| RQ1 Portability | `sample --execute` per engine; overlay LOC; `--mine-overlay` | query validity with manual overlays (600 test cases): DuckDB 96.3 %, SQLite 97.7 % (7 Nov); Turso 93.3 %, DataFusion 79.4 % (8 Nov; DataFusion overlay still in progress, B4); mined overlay alone: DuckDB statement validity 32.1 % to 44.1 % in one round |
| RQ2 Bugs | `docs/generalized/LEDGER.md` | 7 packages; 3 fixed upstream before filing (Turso T-01, T-02; DuckDB D-02); 3 filed with fixes (Turso T-05, DuckDB D-01, DataFusion DF-01); 1 ready (DF-02) |
| RQ3 Rule feedback, targeting, seeds | `configs/eval/e4_rules_*`, `e4_seeds_*` | smoke only [TBD] |
| RQ4 Data synthesis | `configs/eval/e4_synth_*`, `scripts/eval_c3_vacuity.py` | non-vacuous TLP checks on column predicates 34 % to 40 % (first version, DuckDB) |
| RQ5 Normalizers | `configs/eval/e4_norm_{off,on}` | held-out disagreement DuckDB vs SQLite 28.7 % to 3.6 % |
| RQ6 Baselines | `scripts/baselines/` | [TBD] |
| RQ7 Cost and autonomy | hunt logs, packages | `hunt` round on DataFusion (20 s) produced 3 reproducible package drafts automatically |
| Ground truth | `scripts/coverage/` | 200 SQLite test cases: 69.4 % of optimizer-file lines |

Statistics: medians, Mann-Whitney U, Vargha-Delaney A12, bootstrap 95 % CIs (`pgfuzz report`).

## 5. Discussion and threats to validity

- Rule firing by toggling sees only rules the engine lets us switch off; per-rule traces (DataFusion) are exact.
- Short campaigns on 4 cores; trials and budgets in PLAN.md section 6.
- Benchmark bugs are re-injected fixes, biased toward bugs that already had tests.
- Cross-engine precision measured on a hand-labelled sample.

## 6. Related work

Use the novelty table in PLAN.md section 1.1 (SQLancer and SQLancer++, ShQveL, Sedar, QTRAN, Mozi,
DQP, QPG, WhiteFox, DBcover, HyLLfuzz, Argus, EET, SQLxDiff, ARG, PQS, TQS, Radar), plus grammar
fuzzers (Squirrel, SQLRight, Griffin) and LLM fuzzers (Fuzz4All).

## 7. Conclusion and artifact

Artifact: branch `generalized`; `cd src && python -m pytest -q`; quick start in `src/README.md`.
