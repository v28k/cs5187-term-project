#!/usr/bin/env bash
# E4: every evaluation run, then reports. DRY=1 checks all configs without running them.
#   scripts/eval/run_all.sh [jobs=3]
# Order: (re)generate configs, import suites for the seed arms, run every e4_* experiment,
# build reports (tables, Mann-Whitney U, Vargha-Delaney A12, bootstrap CIs via `pgfuzz report`),
# the precision ledger and the C3 vacuity table. Baselines: scripts/baselines/run_all.sh.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); J=${1:-3}
cd "$ROOT/src"
python "$ROOT/scripts/eval/make_configs.py" ${SECONDS_PER_TRIAL:+--seconds $SECONDS_PER_TRIAL} >/dev/null
for e in duckdb:/root/arbor/duckdb-src/test/sql datafusion:/root/arbor/datafusion-src/datafusion/sqllogictest/test_files \
         sqlite:/root/arbor/sqlite-src/test; do
  eng=${e%%:*}; suite=${SUITES_DIR:+$SUITES_DIR/$eng}; suite=${suite:-${e#*:}}
  if [ -z "${DRY:-}" ] && [ -d "$suite" ] && [ ! -d corpus/suites/$eng ]; then
    python -m pgfuzz -q import-tests "$suite" --out corpus/suites/$eng
  fi
done
fail=0
for c in configs/eval/e4_*.yaml; do
  if [ -n "${DRY:-}" ]; then
    python -m pgfuzz -q run "$c" --dry-run >/dev/null && echo "ok   $c" || { echo "FAIL $c"; fail=1; }
  else
    python -m pgfuzz run "$c" -j "$J"
    python -m pgfuzz report "results/$(basename "$c" .yaml)"
  fi
done
[ -n "${DRY:-}" ] || python -m pgfuzz ledger --out ../docs/generalized/LEDGER.md >/dev/null
exit $fail
