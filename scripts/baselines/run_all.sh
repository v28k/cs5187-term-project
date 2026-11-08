#!/usr/bin/env bash
# E2: all baseline runs of the evaluation plan (same budget and trials as configs/eval).
#   scripts/baselines/run_all.sh [seconds=3600] [trials=4]      DRY=1 prints the commands only
set -euo pipefail
S=${1:-3600}; T=${2:-4}; H=$(dirname "$0")/sqlancer.sh
for t in $(seq 1 "$T"); do
  for job in "duckdb NoREC" "duckdb WHERE" "sqlite3 NoREC" "sqlite3 WHERE"; do
    set -- $job
    if [ -n "${DRY:-}" ]; then echo "$H run $1 $2 $S $t"; else "$H" run "$1" "$2" "$S" "$t"; fi
  done
done
[ -n "${DRY:-}" ] || "$H" summary
