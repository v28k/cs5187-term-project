# Code-coverage ground truth (task C5)

Validates *rule coverage* (the engine-agnostic signal) against line coverage of the optimizer
code. Coverage builds are only used for evaluation; the fuzzer never needs them.

| Script | What it does |
|---|---|
| `sqlite_gcov.sh <sqlite-src> <config> "<arms>" [n] [seed]` | gcov build of the sqlite3 shell (amalgamation, `-O0 --coverage`), replays `n` test cases per arm (`pgfuzz sample`), line coverage per SQLite source file |
| `duckdb_coverage.sh <duckdb-src> <config> "<arms>" [n] [seed]` | same for DuckDB (`--coverage` debug build, lcov over `src/optimizer` and `src/planner`); needs hours and ~20 GB |
| `to_shell.py` | `pgfuzz sample` output -> shell script, one `BEGIN ... ROLLBACK` per test case |
| `gcov_summary.py` | per-file summary of `sqlite3.c.gcov`; `--table` renders arms side by side |
| `correlate.py points.csv` | Spearman rho of rules seen vs optimizer line coverage |

Smoke test (8 Nov 2026, SQLite trunk source, `configs/sqlite.yaml` arm `grammar_mm`, 200 test
cases, seed 1, about 30 s including the build): 50.0 % of all lines, **69.4 % of the
optimizer files** (where.c 63.5 %, select.c 81.0 %, expr.c 78.4 %). Full per-arm runs and the
correlation are future work (docs/generalized/FUTURE_WORK.md).
