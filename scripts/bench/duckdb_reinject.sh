#!/usr/bin/env bash
# E3: build DuckDB with selected bug fixes reverted (bugs re-injected), then verify each bug.
#
#   scripts/bench/duckdb_reinject.sh <duckdb-src> <base-sha> <commits.txt> [workdir]
#
# commits.txt: one fix sha per line (from duckdb_fixes.py, picked by hand: they must revert
# cleanly together). Only src/ is reverted; the fixes' regression tests stay, so after the build
# `unittest <test>` must FAIL for each re-injected bug (verified.txt lists those that do).
# The Python package for campaigns is then built from the same tree (tools/pythonpkg or the
# duckdb-python repository pointed at it); configs/eval/e3_duckdb_reinjected.yaml uses it.
set -euo pipefail
SRC=$(realpath "$1"); BASE=$2; LIST=$(realpath "$3"); WT=${4:-$SRC/../duckdb-reinject-wt}
if [ -d "$WT" ]; then git -C "$WT" checkout -q --detach "$BASE" && git -C "$WT" reset -q --hard
else git -C "$SRC" worktree add -q --detach "$WT" "$BASE"; fi
cd "$WT"
for c in $(grep -v '^#' "$LIST"); do
  git diff "$c^" "$c" -- src | git apply -R --3way \
    || { echo "revert of $c does not apply on $BASE" >&2; exit 1; }
  echo "reverted $(git log -1 --format='%h %s' "$c")"
done
GEN=ninja BUILD_UNITTESTS=1 make release -j"$(nproc)"
: > verified.txt
for c in $(grep -v '^#' "$LIST"); do
  for t in $(git show --name-only --format= "$c" | grep '^test/sql/.*\.test$'); do
    [ -f "$t" ] || continue
    if build/release/test/unittest "$t" >/dev/null 2>&1; then echo "NOT reinjected: $c ($t passes)"
    else echo "$c $t" >> verified.txt; echo "reinjected: $c ($t fails)"; fi
  done
done
echo "$(cut -d' ' -f1 verified.txt | sort -u | wc -l) bugs verified -> $WT/verified.txt"
