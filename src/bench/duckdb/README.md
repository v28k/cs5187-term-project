# DuckDB re-injected bug benchmark (task E3)

1. `python scripts/bench/duckdb_fixes.py <duckdb-src> --since 2026-05-01 --out src/bench/duckdb/candidates.json`
   lists fix commits that change at most 3 C++ files under `src/` and add or change a
   sqllogictest under `test/sql/`. Run on 8 Nov 2026 (DuckDB `main` d4eea3f208): **334
   candidates** (function 99, execution 76, planner 67, optimizer 58, common 52, main 16).
2. Pick about 20 of them (logic bugs in optimizer and planner first) into `commits.txt`.
3. `scripts/bench/duckdb_reinject.sh <duckdb-src> <base-sha> src/bench/duckdb/commits.txt` reverts
   their `src/` changes on the base, builds with unit tests, and keeps a bug only if its own
   regression test now fails (`verified.txt`). On a blob-less partial clone, run
   `git fetch --refetch` first (the revert needs file contents).
4. Build the Python package from the same tree; run the arms of `configs/eval/` against it;
   attribute failures to bugs by re-running each failure on builds with one fix applied back.

Steps 2 to 4 (selection, build, campaigns) are future work: a DuckDB build takes about 1 to 2
hours on 4 cores.
