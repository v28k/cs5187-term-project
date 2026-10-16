#!/usr/bin/env bash
# Print cumulative gcov coverage of a PostgreSQL build tree as one JSON line:
#   {"lines_covered": N, "lines_total": N, "branches_covered": N, "branches_total": N, "functions_covered": N}
#
#   coverage.sh SRC_DIR          collect (used as the executor's coverage_command)
#   coverage.sh SRC_DIR reset    zero the counters and record the totals (coverage_reset_command)
#
# Only the backend and PL/pgSQL are measured. Totals come from an --initial
# capture taken at reset, so the denominator does not grow as new files are hit.
set -uo pipefail

SRC=${1:?usage: coverage.sh SRC_DIR [reset]}
MODE=${2:-collect}
STATE=${COV_STATE:-/tmp/pgfuzz-cov}
mkdir -p "$STATE"

DIRS=(--directory "$SRC/src/backend")
[ -d "$SRC/src/pl/plpgsql/src" ] && DIRS+=(--directory "$SRC/src/pl/plpgsql/src")

major=$(lcov --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1 | cut -d. -f1)
if [ "${major:-1}" -ge 2 ]; then
  RC=(--rc branch_coverage=1 --ignore-errors gcov,source,graph,mismatch,negative,unused,empty,inconsistent,format,count,corrupt)
else
  RC=(--rc lcov_branch_coverage=1)
fi

summary() {  # lcov --summary output -> "lines_hit lines_total branches_hit branches_total functions_hit"
  lcov --summary "$1" "${RC[@]}" 2>&1 | awk '
    /lines\.*:/     { gsub(/[()]/, ""); for (i = 1; i <= NF; i++) if ($i == "of") { lh = $(i-1); lt = $(i+1) } }
    /functions\.*:/ { gsub(/[()]/, ""); for (i = 1; i <= NF; i++) if ($i == "of") { fh = $(i-1) } }
    /branches\.*:/  { gsub(/[()]/, ""); for (i = 1; i <= NF; i++) if ($i == "of") { bh = $(i-1); bt = $(i+1) } }
    END { printf "%d %d %d %d %d\n", lh, lt, bh, bt, fh }'
}

if [ "$MODE" = reset ]; then
  lcov --zerocounters "${DIRS[@]}" -q >/dev/null 2>&1
  lcov --capture --initial "${DIRS[@]}" -o "$STATE/base.info" -q "${RC[@]}" >/dev/null 2>&1
  read -r _ lt _ bt _ < <(summary "$STATE/base.info")
  echo "$lt $bt" > "$STATE/totals"
  echo "{\"reset\": true, \"lines_total\": $lt, \"branches_total\": $bt}"
  exit 0
fi

if ! lcov --capture "${DIRS[@]}" -o "$STATE/cur.info" -q "${RC[@]}" >/dev/null 2>&1; then
  echo '{"lines_covered": 0}'
  exit 0
fi
read -r lh lt bh bt fh < <(summary "$STATE/cur.info")
if [ -s "$STATE/totals" ]; then read -r lt bt < "$STATE/totals"; fi
echo "{\"lines_covered\": $lh, \"lines_total\": $lt, \"branches_covered\": $bh, \"branches_total\": $bt, \"functions_covered\": $fh}"
