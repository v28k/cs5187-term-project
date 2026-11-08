#!/usr/bin/env bash
# C5 (DuckDB, optional): coverage build of the DuckDB shell, then replay of each arm's test
# cases and an lcov summary of src/optimizer/ and src/planner/. A full DuckDB build with
# --coverage takes hours on 4 cores and ~20 GB of disk; run it on a larger machine.
#
#   scripts/coverage/duckdb_coverage.sh <duckdb-src> <config.yaml> "<arm1> <arm2>" [n=2000] [seed=1]
set -euo pipefail
SRC=$(realpath "$1"); CFG=$(realpath "$2"); ARMS=$3; N=${4:-2000}; SEED=${5:-1}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$ROOT/results/coverage/duckdb; BUILD=$OUT/build
mkdir -p "$BUILD"
if [ ! -x "$BUILD/duckdb" ]; then
  cmake -S "$SRC" -B "$BUILD" -G Ninja -DCMAKE_BUILD_TYPE=Debug -DBUILD_EXTENSIONS="" \
        -DCMAKE_C_FLAGS="--coverage" -DCMAKE_CXX_FLAGS="--coverage" -DCMAKE_EXE_LINKER_FLAGS="--coverage"
  cmake --build "$BUILD" --target shell -j"$(nproc)"
  ln -sf "$BUILD/duckdb" "$BUILD/duckdb" 2>/dev/null || true
fi
SCHEMA=$ROOT/src/corpus/duckdb/schema.sql
for arm in $ARMS; do
  A=$OUT/$arm; mkdir -p "$A"
  find "$BUILD" -name '*.gcda' -delete
  ( cd "$ROOT/src" && python -m pgfuzz -q sample "$CFG" --name "$arm" -n "$N" --seed "$SEED" ) \
    | python "$ROOT/scripts/coverage/to_shell.py" > "$A/replay.sql"
  { cat "$SCHEMA"; cat "$A/replay.sql"; } | timeout 7200 "$BUILD/duckdb" -bail=false >/dev/null 2>&1 || true
  lcov --capture --directory "$BUILD" --output-file "$A/all.info" --ignore-errors mismatch,negative >/dev/null
  lcov --extract "$A/all.info" '*/src/optimizer/*' '*/src/planner/*' --output-file "$A/opt.info" >/dev/null
  lcov --summary "$A/opt.info" 2>&1 | tee "$A/summary.txt"
done
