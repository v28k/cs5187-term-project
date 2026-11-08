# Future work (generalized fuzzer)

State on 8 Nov 2026: every task of PLAN.md has code, a script or a first version, and
`cd src && python -m pytest -q` passes. The owner stopped long campaigns and result-chasing on
8 Nov (end-semester exams). What remains is mostly running what exists and measuring; each item
says where to start.

## 1. Run the evaluation (no new code needed)

| Item | Start here | Cost on this 4-core machine |
|---|---|---|
| RQ2-RQ5 arms (rules, synthesis, suite seeds, normalizers) | `scripts/eval/run_all.sh` (`DRY=1` checks the configs) | 11 experiments x 4 trials x 1 h, about 4 days with 3 workers |
| SQLancer baseline (RQ6) | `scripts/baselines/sqlancer.sh build`, then `scripts/baselines/run_all.sh` | 16 runs x 1 h; the build was blocked by the sandbox in this session |
| Code-coverage ground truth (C5) | `scripts/coverage/sqlite_gcov.sh` per arm, `correlate.py` | minutes per arm for SQLite; DuckDB needs a large machine |
| DuckDB re-injected bug benchmark (E3) | `src/bench/duckdb/README.md` (334 candidates mined) | pick ~20, about 2 h per build, then campaigns |
| Long campaigns per engine (E1) | `pgfuzz hunt configs/{duckdb,sqlite,turso,datafusion}.yaml --budget 7200` | as long as wanted; packages appear in `results/hunt/packages` |

## 2. Improve the techniques

- **Data synthesis to the target (C3).** Z3 rows currently go into scratch tables of the test
  case; insert them into the tables the query reads (or derive the query's tables from the
  solution) so the gain on vacuity (34 % to 40 % so far) becomes large.
- **Overlay miner (A3).** Iterate rounds automatically (mine, apply, re-sample), mine
  `%dropopt` for group alternatives and `%replace` rewrites from error messages (unknown
  function -> engine name); report mined vs manual overlay lines per engine (RQ1).
- **DataFusion validity (B4).** 79.4 % of queries are valid; mine the overlay on DataFusion and
  extend `datafusion.data.yaml` until 95 %.
- **Rule targeting (C2).** Evaluate against rule-feedback-only; add near-miss mutation; index
  imported suite seeds by the rules they fire (C6 -> C2).
- **Rule-firing cost (C1).** Measure overhead and cache firing results by plan shape.
- **Autonomous triage (D2).** Cross-engine signature dedup, duplicate search in the cloned
  repositories' history, newest-build reproduction inside `hunt`; nightly upgrades and a
  bandit over engines and oracles in `hunt` (D1).
- **Packages (D3).** Pass the engine executor to `make_package` inside `hunt` so wrong-result
  packages carry observed rows; map the localized rule to its source file.

## 3. More engines (B5, decision D2)

- **ClickHouse via chDB** and **Polars SQL**: both run in-process from pip; a driver is
  ~150 lines (`pgfuzz/targets/datafusion_executor.py` is the model), plus an overlay mined with
  `--mine-overlay` and a schema file.
- MySQL / MariaDB / CockroachDB / TiDB need servers whose downloads this network blocked.

## 4. LLM phase (Phase L, deferred by the owner's decision D6)

L1 rule solver at roadblocks, L2 overlay patches, L3 normalizer labels, L4 root-cause summaries,
L5 recent-commit context. The course project's LLM arm (`pgfuzz/llm/`, gate) is the base.

## 5. Paper (E5)

`docs/generalized/paper/OUTLINE.md` has the structure, claims and the first numbers; venue,
authorship and the AI statement are open decisions (PROGRESS.md).

## 6. Hygiene (P1-P4)

Rename `pgfuzz` to `arbor` with an alias (P1); keep only the newest engine builds (P4).
