#!/usr/bin/env bash
# C5 (code-coverage ground truth, SQLite): build a gcov-instrumented sqlite3 shell from a
# SQLite source tree, replay the test cases each generator arm produces, and report line
# coverage per SQLite source file (where.c, select.c, expr.c, ...: the optimizer files).
#
#   scripts/coverage/sqlite_gcov.sh <sqlite-src> <config.yaml> "<arm1> <arm2>" [n=2000] [seed=1]
#
# Output: results/coverage/sqlite/<arm>/summary.json (per-file line coverage) and
# results/coverage/sqlite/summary.md. Each arm is replayed in a fresh build directory copy of
# the .gcda counters, so arms do not mix. Rule coverage for the same test cases comes from the
# campaign logs (rules_seen); scripts/coverage/correlate.py computes Spearman rho between them.
set -euo pipefail
SRC=$(realpath "$1"); CFG=$(realpath "$2"); ARMS=$3; N=${4:-2000}; SEED=${5:-1}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$ROOT/results/coverage/sqlite; BUILD=$OUT/build
mkdir -p "$BUILD"
if [ ! -x "$BUILD/sqlite3" ]; then
  ( cd "$BUILD" && "$SRC/configure" --disable-tcl >/dev/null && make -j"$(nproc)" sqlite3.c shell.c >/dev/null )
  F="-O0 -g --coverage -DSQLITE_DEBUG -DSQLITE_ENABLE_STAT4 -DSQLITE_ENABLE_MATH_FUNCTIONS -I$BUILD"
  ( cd "$BUILD" && gcc $F -c sqlite3.c -o sqlite3.o && gcc $F -c shell.c -o shell.o \
      && gcc --coverage sqlite3.o shell.o -o sqlite3 -lm -ldl -lpthread )
fi
SCHEMA=$ROOT/src/corpus/sqlite/schema.sql
for arm in $ARMS; do
  A=$OUT/$arm; mkdir -p "$A"
  find "$BUILD" -name '*.gcda' -delete
  ( cd "$ROOT/src" && python -m pgfuzz -q sample "$CFG" --name "$arm" -n "$N" --seed "$SEED" ) \
    | python "$ROOT/scripts/coverage/to_shell.py" > "$A/replay.sql"
  { echo ".bail off"; cat "$SCHEMA"; cat "$A/replay.sql"; } | timeout 3600 "$BUILD/sqlite3" :memory: >/dev/null 2>&1 || true
  ( cd "$BUILD" && gcov -o "$BUILD" sqlite3.c >/dev/null 2>&1 && cp sqlite3.c.gcov "$A/" )
  python "$ROOT/scripts/coverage/gcov_summary.py" "$A/sqlite3.c.gcov" > "$A/summary.json"
done
python "$ROOT/scripts/coverage/gcov_summary.py" --table "$OUT"/*/summary.json > "$OUT/summary.md"
cat "$OUT/summary.md"
